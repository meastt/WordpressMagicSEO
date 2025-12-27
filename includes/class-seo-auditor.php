<?php
/**
 * Magic SEO Auditor
 * 
 * Core audit engine that crawls site and performs SEO checks.
 * Ported from Python TechnicalSEOAuditor for native WordPress execution.
 */

if (!defined('ABSPATH')) {
    exit;
}

class Magic_SEO_Auditor {
    
    /**
     * Issue impact weights for score calculation
     */
    const ISSUE_WEIGHTS = [
        'noindex' => 10,
        'title_presence' => 9,
        'h1_presence' => 9,
        'meta_description_presence' => 8,
        'title_length' => 7,
        'meta_description_length' => 7,
        'multiple_h1s' => 7,
        'schema_markup' => 6,
        'heading_hierarchy' => 5,
        'image_alt_text' => 5,
        'internal_links' => 4,
        'external_links' => 4,
        'broken_links' => 3,
    ];
    
    /**
     * Rate limit delay between requests (seconds)
     */
    private $rate_limit = 1;
    
    /**
     * Request timeout (seconds)
     */
    private $timeout = 30;
    
    /**
     * Get all URLs from sitemap
     */
    public function get_sitemap_urls($site_url) {
        $site_url = trailingslashit($site_url);
        $sitemap_urls = [];
        
        // First, check robots.txt for sitemap location
        $robots_sitemap = $this->get_sitemap_from_robots($site_url);
        if (!empty($robots_sitemap)) {
            error_log("Magic SEO: Found sitemap in robots.txt: " . $robots_sitemap);
            $urls = $this->parse_sitemap($robots_sitemap);
            if (!empty($urls)) {
                return array_unique($urls);
            }
        }
        
        // Try common sitemap locations
        $sitemap_paths = [
            // WordPress core (5.5+)
            'wp-sitemap.xml',
            // Yoast SEO
            'sitemap_index.xml',
            'sitemap.xml',
            'post-sitemap.xml',
            'page-sitemap.xml',
            // RankMath
            'sitemap_index.xml',
            // All in One SEO
            'sitemap.xml',
            // Generic
            'sitemaps.xml',
            'sitemap/sitemap.xml',
        ];
        
        foreach ($sitemap_paths as $path) {
            $sitemap_url = $site_url . $path;
            error_log("Magic SEO: Trying sitemap at: " . $sitemap_url);
            $urls = $this->parse_sitemap($sitemap_url);
            if (!empty($urls)) {
                error_log("Magic SEO: Found " . count($urls) . " URLs in: " . $sitemap_url);
                $sitemap_urls = array_merge($sitemap_urls, $urls);
                // If we got URLs from main sitemap, stop searching
                if (count($urls) > 5) {
                    break;
                }
            }
        }
        
        // Remove duplicates
        $sitemap_urls = array_unique($sitemap_urls);
        
        error_log("Magic SEO: Total URLs found: " . count($sitemap_urls));
        
        return $sitemap_urls;
    }
    
    /**
     * Check robots.txt for Sitemap: directive
     */
    private function get_sitemap_from_robots($site_url) {
        $robots_url = trailingslashit($site_url) . 'robots.txt';
        
        $response = wp_remote_get($robots_url, [
            'timeout' => 10,
            'sslverify' => false,
        ]);
        
        if (is_wp_error($response)) {
            return null;
        }
        
        $body = wp_remote_retrieve_body($response);
        
        // Look for Sitemap: directive (case insensitive)
        if (preg_match('/^Sitemap:\s*(.+)$/mi', $body, $matches)) {
            return trim($matches[1]);
        }
        
        return null;
    }
    
    /**
     * Parse a sitemap XML file
     */
    private function parse_sitemap($sitemap_url) {
        $response = wp_remote_get($sitemap_url, [
            'timeout' => $this->timeout,
            'sslverify' => false,
        ]);
        
        if (is_wp_error($response)) {
            return [];
        }
        
        $body = wp_remote_retrieve_body($response);
        if (empty($body)) {
            return [];
        }
        
        $urls = [];
        
        // Suppress XML errors
        libxml_use_internal_errors(true);
        $xml = simplexml_load_string($body);
        
        if ($xml === false) {
            return [];
        }
        
        // Check if it's a sitemap index
        if (isset($xml->sitemap)) {
            foreach ($xml->sitemap as $sitemap) {
                $sub_urls = $this->parse_sitemap((string)$sitemap->loc);
                $urls = array_merge($urls, $sub_urls);
            }
        }
        
        // Regular sitemap with URLs
        if (isset($xml->url)) {
            foreach ($xml->url as $url) {
                $urls[] = (string)$url->loc;
            }
        }
        
        return $urls;
    }
    
    /**
     * Audit a single URL
     */
    public function audit_url($url) {
        $response = wp_remote_get($url, [
            'timeout' => $this->timeout,
            'sslverify' => false,
            'user-agent' => 'Mozilla/5.0 (compatible; MagicSEO-Auditor/1.1; +https://magicseo.com)',
        ]);
        
        if (is_wp_error($response)) {
            return [
                'url' => $url,
                'error' => $response->get_error_message(),
                'issues' => [],
            ];
        }
        
        $status_code = wp_remote_retrieve_response_code($response);
        $html = wp_remote_retrieve_body($response);
        
        if ($status_code !== 200) {
            return [
                'url' => $url,
                'status_code' => $status_code,
                'issues' => [],
            ];
        }
        
        // Run all checks
        $issues = [];
        
        // On-page checks
        $issues['onpage'] = array_merge(
            $this->check_title($html),
            $this->check_meta_description($html),
            $this->check_h1($html, $url),
            $this->check_headings($html)
        );
        
        // Image checks
        $issues['images'] = $this->check_images($html);
        
        // Link checks
        $issues['links'] = $this->check_links($html, $url);
        
        // Technical checks
        $issues['technical'] = array_merge(
            $this->check_noindex($html),
            $this->check_schema($html)
        );
        
        return [
            'url' => $url,
            'status_code' => $status_code,
            'issues' => $issues,
        ];
    }
    
    /**
     * Run full site audit
     */
    public function audit_site($site_url, $max_urls = null, $progress_callback = null) {
        $urls = $this->get_sitemap_urls($site_url);
        
        if (empty($urls)) {
            return [
                'site_url' => $site_url,
                'error' => 'Could not find sitemap or no URLs found',
                'total_urls_checked' => 0,
                'urls' => [],
            ];
        }
        
        if ($max_urls !== null && $max_urls > 0) {
            $urls = array_slice($urls, 0, $max_urls);
        }
        
        $results = [];
        $total = count($urls);
        
        foreach ($urls as $index => $url) {
            // Audit URL
            $result = $this->audit_url($url);
            $results[] = $result;
            
            // Progress callback
            if (is_callable($progress_callback)) {
                $progress_callback([
                    'current' => $index + 1,
                    'total' => $total,
                    'url' => $url,
                    'percent' => round(($index + 1) / $total * 100),
                ]);
            }
            
            // Rate limiting (except for last URL)
            if ($index < $total - 1) {
                sleep($this->rate_limit);
            }
        }
        
        // Calculate summary
        $summary = $this->calculate_summary($results);
        
        return [
            'site_url' => $site_url,
            'audit_date' => current_time('c'),
            'total_urls_checked' => count($results),
            'summary' => $summary,
            'urls' => $results,
        ];
    }
    
    /**
     * Calculate audit summary and score
     */
    private function calculate_summary($results) {
        $critical = 0;
        $warnings = 0;
        $passed = 0;
        $weighted_penalty = 0;
        $max_weight = 0;
        
        foreach ($results as $result) {
            if (isset($result['error'])) {
                continue;
            }
            
            foreach ($result['issues'] as $category => $issues) {
                foreach ($issues as $issue) {
                    $weight = self::ISSUE_WEIGHTS[$issue['check_name']] ?? 3;
                    $max_weight += $weight;
                    
                    if ($issue['status'] === 'critical') {
                        $critical++;
                        $weighted_penalty += $weight;
                    } elseif ($issue['status'] === 'warning') {
                        $warnings++;
                        $weighted_penalty += $weight * 0.3;
                    } else {
                        $passed++;
                    }
                }
            }
        }
        
        return [
            'critical_issues' => $critical,
            'warnings' => $warnings,
            'passed' => $passed,
            'weighted_penalty' => $weighted_penalty,
            'max_weight' => $max_weight,
        ];
    }
    
    // ========== CHECK METHODS ==========
    
    /**
     * Check page title
     */
    private function check_title($html) {
        $issues = [];
        
        // Extract title
        preg_match('/<title[^>]*>([^<]*)<\/title>/i', $html, $matches);
        $title = isset($matches[1]) ? trim($matches[1]) : '';
        
        if (empty($title)) {
            $issues[] = [
                'check_name' => 'title_presence',
                'status' => 'critical',
                'severity' => 'critical',
                'message' => 'Page is missing a title tag',
                'value' => null,
            ];
        } else {
            $length = strlen($title);
            
            if ($length < 30) {
                $issues[] = [
                    'check_name' => 'title_length',
                    'status' => 'warning',
                    'severity' => 'warning',
                    'message' => "Title too short ({$length} chars, recommended 30-60)",
                    'value' => $length,
                ];
            } elseif ($length > 60) {
                $issues[] = [
                    'check_name' => 'title_length',
                    'status' => 'warning',
                    'severity' => 'warning',
                    'message' => "Title too long ({$length} chars, recommended 30-60)",
                    'value' => $length,
                ];
            } else {
                $issues[] = [
                    'check_name' => 'title_presence',
                    'status' => 'optimal',
                    'severity' => 'info',
                    'message' => 'Title tag is present and optimal length',
                    'value' => $length,
                ];
            }
        }
        
        return $issues;
    }
    
    /**
     * Check meta description
     */
    private function check_meta_description($html) {
        $issues = [];
        
        // Extract meta description
        // Handles name before content, content before name, and varying quotes/spaces
        preg_match('/<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\'][^>]*>/i', $html, $matches);
        if (empty($matches)) {
            preg_match('/<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\'][^>]*>/i', $html, $matches);
        }
        
        // Fallback: matches any tag with name="description" and grabs the content attribute anywhere in the tag
        if (empty($matches)) {
            preg_match('/<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\'][^>]*>/is', $html, $matches);
        }
        if (empty($matches)) {
            preg_match('/<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\'][^>]*>/is', $html, $matches);
        }
        
        $description = isset($matches[1]) ? trim($matches[1]) : '';
        
        // AIOSEO and some other plugins might output specific markers we can look for if the above fails
        // But generally standard meta description is enough
        
        if (empty($description)) {
            $issues[] = [
                'check_name' => 'meta_description_presence',
                'status' => 'critical',
                'severity' => 'critical',
                'message' => 'Page is missing a meta description',
                'value' => null,
            ];
        } else {
            $length = strlen($description);
            
            if ($length < 70) {
                $issues[] = [
                    'check_name' => 'meta_description_length',
                    'status' => 'warning',
                    'severity' => 'warning',
                    'message' => "Meta description too short ({$length} chars, recommended 70-160)",
                    'value' => $length,
                ];
            } elseif ($length > 160) {
                $issues[] = [
                    'check_name' => 'meta_description_length',
                    'status' => 'warning',
                    'severity' => 'warning',
                    'message' => "Meta description too long ({$length} chars, recommended 70-160)",
                    'value' => $length,
                ];
            } else {
                $issues[] = [
                    'check_name' => 'meta_description_presence',
                    'status' => 'optimal',
                    'severity' => 'info',
                    'message' => 'Meta description is present and optimal length',
                    'value' => $length,
                ];
            }
        }
        
        return $issues;
    }
    
    /**
     * Check H1 tags
     */
    private function check_h1($html, $url = '') {
        $issues = [];
        
        // Skip H1 check for archive/category/tag pages as they often don't have explicit H1s in themes
        if (!empty($url)) {
            $path = parse_url($url, PHP_URL_PATH);
            if (preg_match('/\/(category|tag|author|archive)\//i', $path)) {
                return [];
            }
        }
        
        preg_match_all('/<h1[^>]*>([^<]*)<\/h1>/i', $html, $matches);
        $h1_count = count($matches[0]);
        
        if ($h1_count === 0) {
            $issues[] = [
                'check_name' => 'h1_presence',
                'status' => 'critical',
                'severity' => 'critical',
                'message' => 'Page is missing an H1 heading',
                'value' => 0,
            ];
        } elseif ($h1_count > 1) {
            $issues[] = [
                'check_name' => 'multiple_h1s',
                'status' => 'warning',
                'severity' => 'warning',
                'message' => "Page has multiple H1 tags ({$h1_count} found)",
                'value' => $h1_count,
            ];
        } else {
            $issues[] = [
                'check_name' => 'h1_presence',
                'status' => 'optimal',
                'severity' => 'info',
                'message' => 'Single H1 heading present',
                'value' => 1,
            ];
        }
        
        return $issues;
    }
    
    /**
     * Check heading hierarchy
     */
    private function check_headings($html) {
        $issues = [];
        
        // Find all headings
        preg_match_all('/<h([1-6])[^>]*>/i', $html, $matches);
        
        if (!empty($matches[1])) {
            $levels = array_map('intval', $matches[1]);
            $has_skip = false;
            
            for ($i = 1; $i < count($levels); $i++) {
                if ($levels[$i] > $levels[$i-1] + 1) {
                    $has_skip = true;
                    break;
                }
            }
            
            if ($has_skip) {
                $issues[] = [
                    'check_name' => 'heading_hierarchy',
                    'status' => 'warning',
                    'severity' => 'warning',
                    'message' => 'Heading levels are skipped (e.g., H2 to H4)',
                    'value' => implode(',', $levels),
                ];
            } else {
                $issues[] = [
                    'check_name' => 'heading_hierarchy',
                    'status' => 'optimal',
                    'severity' => 'info',
                    'message' => 'Heading hierarchy is correct',
                    'value' => null,
                ];
            }
        }
        
        return $issues;
    }
    
    /**
     * Check images for alt text
     */
    private function check_images($html) {
        $issues = [];
        
        preg_match_all('/<img[^>]+>/i', $html, $matches);
        $total_images = count($matches[0]);
        $missing_alt = 0;
        
        foreach ($matches[0] as $img) {
            if (!preg_match('/alt=["\'][^"\']+["\']/i', $img)) {
                $missing_alt++;
            }
        }
        
        if ($missing_alt > 0) {
            $issues[] = [
                'check_name' => 'image_alt_text',
                'status' => 'warning',
                'severity' => 'warning',
                'message' => "{$missing_alt} of {$total_images} images missing alt text",
                'value' => $missing_alt,
            ];
        } elseif ($total_images > 0) {
            $issues[] = [
                'check_name' => 'image_alt_text',
                'status' => 'optimal',
                'severity' => 'info',
                'message' => "All {$total_images} images have alt text",
                'value' => 0,
            ];
        }
        
        return $issues;
    }
    
    /**
     * Check internal and external links
     */
    private function check_links($html, $base_url) {
        $issues = [];
        $parsed_base = parse_url($base_url);
        $base_host = $parsed_base['host'] ?? '';
        
        preg_match_all('/<a[^>]+href=["\']([^"\']+)["\'][^>]*>/i', $html, $matches);
        
        $internal = 0;
        $external = 0;
        
        foreach ($matches[1] as $href) {
            if (strpos($href, '#') === 0 || strpos($href, 'javascript:') === 0 || strpos($href, 'mailto:') === 0) {
                continue;
            }
            
            $parsed = parse_url($href);
            $link_host = $parsed['host'] ?? '';
            
            if (empty($link_host) || $link_host === $base_host || strpos($link_host, $base_host) !== false) {
                $internal++;
            } else {
                $external++;
            }
        }
        
        if ($internal < 3) {
            $issues[] = [
                'check_name' => 'internal_links',
                'status' => 'warning',
                'severity' => 'warning',
                'message' => "Only {$internal} internal links (recommended: 3+)",
                'value' => $internal,
            ];
        } else {
            $issues[] = [
                'check_name' => 'internal_links',
                'status' => 'optimal',
                'severity' => 'info',
                'message' => "{$internal} internal links found",
                'value' => $internal,
            ];
        }
        
        if ($external === 0) {
            $issues[] = [
                'check_name' => 'external_links',
                'status' => 'warning',
                'severity' => 'warning',
                'message' => 'No external links found',
                'value' => 0,
            ];
        } else {
            $issues[] = [
                'check_name' => 'external_links',
                'status' => 'optimal',
                'severity' => 'info',
                'message' => "{$external} external links found",
                'value' => $external,
            ];
        }
        
        return $issues;
    }
    
    /**
     * Check for noindex tag
     */
    private function check_noindex($html) {
        $issues = [];
        
        $has_noindex = preg_match('/<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex[^"\']*["\'][^>]*>/i', $html);
        
        if ($has_noindex) {
            $issues[] = [
                'check_name' => 'noindex',
                'status' => 'critical',
                'severity' => 'critical',
                'message' => 'Page has noindex tag - will not appear in search',
                'value' => true,
            ];
        } else {
            $issues[] = [
                'check_name' => 'noindex',
                'status' => 'optimal',
                'severity' => 'info',
                'message' => 'Page is indexable',
                'value' => false,
            ];
        }
        
        return $issues;
    }
    
    /**
     * Check for schema markup
     */
    private function check_schema($html) {
        $issues = [];
        
        $has_schema = preg_match('/<script[^>]+type=["\']application\/ld\+json["\'][^>]*>/i', $html);
        
        if (!$has_schema) {
            $issues[] = [
                'check_name' => 'schema_markup',
                'status' => 'warning',
                'severity' => 'warning',
                'message' => 'No structured data (JSON-LD) found',
                'value' => false,
            ];
        } else {
            $issues[] = [
                'check_name' => 'schema_markup',
                'status' => 'optimal',
                'severity' => 'info',
                'message' => 'Structured data present',
                'value' => true,
            ];
        }
        
        return $issues;
    }
}
