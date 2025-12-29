<?php
/**
 * Magic SEO Fixer
 * 
 * Applies SEO fixes via WordPress REST API.
 * Supports native WordPress and common SEO plugins (Yoast, RankMath).
 */

if (!defined('ABSPATH')) {
    exit;
}

class Magic_SEO_Fixer {
    
    /**
     * WordPress site credentials
     */
    private $site_url;
    private $username;
    private $password;
    
    private $python_engine_url;
    private $use_ai;
    
    /**
     * Constructor
     */
    public function __construct($site_url = null, $username = null, $password = null) {
        $this->site_url = $site_url ?: home_url();
        
        $settings = get_option('magic_seo_settings', []);
        $this->python_engine_url = $settings['python_engine_url'] ?? 'http://localhost:5000';
        $this->use_ai = $settings['use_ai_fixes'] ?? true;
        
        // If credentials not passed, try to load from settings for current site
        if (empty($username) && !empty($settings['sites'])) {
            $current_site = $this->site_url;
            foreach ($settings['sites'] as $site) {
                if (!empty($site['site_url']) && strpos($current_site, rtrim($site['site_url'], '/')) !== false) {
                    $username = $site['username'] ?? null;
                    // Decrypt the app_password which is stored encrypted
                    $encrypted_pw = $site['app_password'] ?? null;
                    $password = $this->decrypt_value($encrypted_pw);
                    break;
                }
            }
        }
        
        $this->username = $username;
        $this->password = $password;
    }
    
    /**
     * Decrypt a value encrypted by Magic_SEO class
     */
    private function decrypt_value($encrypted) {
        if (empty($encrypted)) return '';
        $key = wp_salt('auth');
        $iv = substr(hash('sha256', wp_salt('secure_auth')), 0, 16);
        return openssl_decrypt(base64_decode($encrypted), 'AES-256-CBC', $key, 0, $iv);
    }
    
    /**
     * Get post ID from URL
     */
    public function get_post_id_from_url($url) {
        $url_lower = strtolower($url);
        
        // Prioritize Category/Tag if URL pattern matches
        if (strpos($url_lower, '/category/') !== false) {
            if (preg_match('/\/category\/(.+?)\/?$/', $url, $matches)) {
                $path_parts = explode('/', trim($matches[1], '/'));
                $slug = end($path_parts);
                $term = get_term_by('slug', $slug, 'category');
                if ($term) return 'term_' . $term->term_id;
            }
        }

        if (strpos($url_lower, '/tag/') !== false) {
            if (preg_match('/\/tag\/(.+?)\/?$/', $url, $matches)) {
                $path_parts = explode('/', trim($matches[1], '/'));
                $slug = end($path_parts);
                $term = get_term_by('slug', $slug, 'post_tag');
                if ($term) return 'term_' . $term->term_id;
            }
        }

        // Search by slug fallback
        $path = parse_url($url, PHP_URL_PATH);
        $slug = basename($path);
        
        // Try page/post next
        $post_id = url_to_postid($url);
        if ($post_id) {
            return $post_id;
        }

        // Try category by slug directly
        $term = get_term_by('slug', $slug, 'category');
        if ($term) return 'term_' . $term->term_id;

        // Try tag by slug directly
        $term = get_term_by('slug', $slug, 'post_tag');
        if ($term) return 'term_' . $term->term_id;
        
        // For remote sites, query via REST API
        if ($this->site_url !== home_url()) {
            $response = $this->api_request('GET', 'wp/v2/posts', [
                'slug' => $slug,
            ]);
            
            if (!is_wp_error($response) && !empty($response)) {
                return $response[0]['id'] ?? null;
            }
        }
        
        return null;
    }
    
    public function fix_title($id, $new_title = null) {
        $is_term = (strpos($id, 'term_') === 0);
        $term_id = $is_term ? (int)str_replace('term_', '', $id) : null;
        $post_id = !$is_term ? (int)$id : null;

        if (!$is_term) {
            $post = get_post($post_id);
            if (!$post) return ['success' => false, 'message' => 'Post not found'];
        } else {
            $term = get_term($term_id);
            if (!$term) return ['success' => false, 'message' => 'Term not found'];
        }
        
        // Try AI fix first if enabled
        if ($this->use_ai && !empty($this->python_engine_url)) {
            $ai_result = $this->apply_ai_fix($id, 'title_length');
            if ($ai_result && $ai_result['success']) {
                if ($is_term) {
                    $this->update_term_metadata($term_id, 'title', $ai_result['value']);
                } else {
                    $this->update_metadata($post_id, 'title', $ai_result['value']);
                }
                return $ai_result;
            }
        }
        
        // Generate title if not provided (Fallback)
        if (empty($new_title)) {
            $new_title = $is_term ? $term->name : $post->post_title;
            $new_title = $this->generate_seo_title_manual($new_title);
        }
        
        if ($is_term) {
            $this->update_term_metadata($term_id, 'title', $new_title);
        } else {
            $this->update_metadata($post_id, 'title', $new_title);
        }
        
        return [
            'success' => true,
            'message' => 'Title updated',
            'value' => $new_title,
        ];
    }
    
    public function fix_meta_description($id, $description = null) {
        $is_term = (strpos($id, 'term_') === 0);
        $term_id = $is_term ? (int)str_replace('term_', '', $id) : null;
        $post_id = !$is_term ? (int)$id : null;

        if (!$is_term) {
            $post = get_post($post_id);
            if (!$post) return ['success' => false, 'message' => 'Post not found'];
        } else {
            $term = get_term($term_id);
            if (!$term) return ['success' => false, 'message' => 'Term not found'];
        }

        // Try AI fix first if enabled
        if ($this->use_ai && !empty($this->python_engine_url)) {
            $ai_result = $this->apply_ai_fix($id, 'meta_description_length');
            if ($ai_result && $ai_result['success']) {
                if ($is_term) {
                    $this->update_term_metadata($term_id, 'meta_description', $ai_result['value']);
                } else {
                    $this->update_metadata($post_id, 'meta_description', $ai_result['value']);
                }
                return $ai_result;
            }
        }
        
        // Generate description if not provided (Fallback)
        if (empty($description)) {
            if ($is_term) {
                $description = !empty($term->description) ? $term->description : $term->name;
            } else {
                $description = $this->generate_meta_description($post);
            }
        }
        
        if ($is_term) {
            $this->update_term_metadata($term_id, 'meta_description', $description);
        } else {
            $this->update_metadata($post_id, 'meta_description', $description);
        }
        
        return [
            'success' => true,
            'message' => 'Meta description updated',
            'value' => $description,
        ];
    }
    
    /**
     * Fix multiple H1s by downgrading extras to H2 and ensuring one primary H1
     */
    public function fix_multiple_h1s($post_id) {
        $post = get_post($post_id);
        if (!$post) {
            return [
                'success' => false,
                'message' => 'Post not found',
            ];
        }
        
        // Try AI fix first if enabled
        if ($this->use_ai && !empty($this->python_engine_url)) {
            $ai_result = $this->apply_ai_fix($post_id, 'multiple_h1s');
            if ($ai_result && $ai_result['success']) {
                return $ai_result;
            }
        }

        // 1. Downgrade existing H1s to H2 in the content
        $content = preg_replace('/<h1([^>]*)>(.*?)<\/h1>/i', '<h2$1>$2</h2>', $post->post_content);
        
        // 2. Add the proper H1 at the top (standard for most themes)
        $h1_text = $post->post_title;
        $new_content = "<h1>{$h1_text}</h1>\n\n" . $content;
        
        wp_update_post([
            'ID' => $post_id,
            'post_content' => $new_content,
        ]);
        
        return [
            'success' => true,
            'message' => 'Multiple H1s resolved: downgraded extras to H2 and added primary H1',
            'value' => $h1_text,
        ];
    }
    
    /**
     * Fix missing H1 by prepending to content
     */
    public function fix_h1($post_id, $h1_text = null) {
        $post = get_post($post_id);
        if (!$post) {
            return [
                'success' => false,
                'message' => 'Post not found',
            ];
        }
        
        // Try AI fix first if enabled
        if ($this->use_ai && !empty($this->python_engine_url)) {
            $ai_result = $this->apply_ai_fix($post_id, 'h1_presence');
            if ($ai_result && $ai_result['success']) {
                return $ai_result;
            }
        }

        // Check if content already has H1
        if (preg_match('/<h1[^>]*>/i', $post->post_content)) {
            return [
                'success' => true,
                'message' => 'H1 already exists in content',
                'value' => null,
            ];
        }
        
        // Use post title if no H1 text provided
        if (empty($h1_text)) {
            $h1_text = $post->post_title;
        }
        
        // Prepend H1 to content
        $new_content = "<h1>{$h1_text}</h1>\n\n" . $post->post_content;
        
        wp_update_post([
            'ID' => $post_id,
            'post_content' => $new_content,
        ]);
        
        return [
            'success' => true,
            'message' => 'H1 added to content',
            'value' => $h1_text,
        ];
    }
    
    /**
     * Batch fix issues by type
     */
    public function fix_batch($issue_type, $urls) {
        $results = [];
        
        foreach ($urls as $url) {
            $post_id = $this->get_post_id_from_url($url);
            
            if (!$post_id) {
                $results[] = [
                    'url' => $url,
                    'success' => false,
                    'message' => 'Could not find post ID for URL',
                ];
                continue;
            }
            
            switch ($issue_type) {
                case 'title_presence':
                case 'title_length':
                    $result = (strpos($post_id, 'term_') === 0) 
                        ? $this->apply_ai_fix($post_id, 'title_length')
                        : $this->fix_title($post_id);
                    break;
                    
                case 'meta_description_presence':
                case 'meta_description_length':
                    $result = (strpos($post_id, 'term_') === 0)
                        ? $this->apply_ai_fix($post_id, 'meta_description_length')
                        : $this->fix_meta_description($post_id);
                    break;
                    
                case 'h1_presence':
                    $result = $this->fix_h1($post_id);
                    break;
                    
                case 'multiple_h1s':
                    $result = $this->fix_multiple_h1s($post_id);
                    break;

                case 'internal_links':
                    $result = $this->apply_ai_fix($post_id, 'internal_links');
                    break;

                case 'content_length':
                    $result = $this->apply_ai_fix($post_id, 'content_length');
                    break;
                    
                default:
                    $result = [
                        'success' => false,
                        'message' => "No automated fix available for '{$issue_type}'",
                    ];
            }
            
            $result['url'] = $url;
            $result['post_id'] = $post_id;
            $results[] = $result;
        }
        
        return $results;
    }
    
    // ========== HELPER METHODS ==========
    
    /**
     * Check if Yoast SEO is active
     */
    private function has_yoast() {
        return defined('WPSEO_VERSION') || class_exists('WPSEO_Meta');
    }
    
    /**
     * Check if RankMath is active
     */
    private function has_rankmath() {
        return defined('RANK_MATH_VERSION') || class_exists('RankMath');
    }
    
    /**
     * Check if All in One SEO is active
     */
    private function has_aioseo() {
        return defined('AIOSEO_VERSION') || class_exists('AIOSEO\Plugin\AIOSEO');
    }
    
    private function generate_seo_title($post) {
        $title = $post->post_title;
        $site_name = get_bloginfo('name');
        $site_separator = ' - ';
        
        // Total desired limit for the final <title> tag
        $hard_limit = 60;
        
        // If title is already very long, truncate it aggressively
        // We leave room for the site name (approx 15-20 chars)
        // Most SEO plugins append site name, so we target ~45 chars for the core title
        $safe_title_limit = 45;
        
        if (strlen($title) > $safe_title_limit) {
            return substr($title, 0, $safe_title_limit - 3) . '...';
        }
        
        // If title is short, we can safely append the site name ourselves
        if (strlen($title) < 30) {
            $with_site = "{$title}{$site_separator}{$site_name}";
            if (strlen($with_site) <= $hard_limit) {
                return $with_site;
            }
        }
        
        return $title;
    }
    
    /**
     * Robust meta update for posts/pages
     */
    private function update_metadata($post_id, $type, $value) {
        // Yoast
        if ($this->has_yoast()) {
            $key = ($type === 'title') ? '_yoast_wpseo_title' : '_yoast_wpseo_metadesc';
            update_post_meta($post_id, $key, $value);
        }

        // RankMath
        if ($this->has_rankmath()) {
            $key = ($type === 'title') ? 'rank_math_title' : 'rank_math_description';
            update_post_meta($post_id, $key, $value);
        }

        // AIOSEO
        if ($this->has_aioseo()) {
            $key = ($type === 'title') ? 'title' : 'description';
            $this->update_aioseo_data($post_id, [$key => $value]);
            // Compat keys
            update_post_meta($post_id, ($type === 'title' ? '_aioseo_title' : '_aioseo_description'), $value);
        }

        // Native fallbacks
        if ($type === 'title') {
            wp_update_post(['ID' => $post_id, 'post_title' => $value]);
        }
    }

    /**
     * Robust meta update for Terms (Categories/Tags)
     */
    private function update_term_metadata($term_id, $type, $value) {
        // Yoast Terms
        if ($this->has_yoast()) {
            $key = ($type === 'title') ? 'wpseo_title' : 'wpseo_desc';
            update_term_meta($term_id, $key, $value);
        }

        // RankMath Terms
        if ($this->has_rankmath()) {
            $key = ($type === 'title') ? 'rank_math_title' : 'rank_math_description';
            update_term_meta($term_id, $key, $value);
        }

        // AIOSEO Terms
        if ($this->has_aioseo()) {
            $key = ($type === 'title') ? 'title' : 'description';
            $this->update_aioseo_term_data($term_id, [$key => $value]);
        }

        // Standard WP description fallback (if applicable and type is meta_description)
        if ($type === 'meta_description') {
            wp_update_term($term_id, get_term($term_id)->taxonomy, ['description' => $value]);
        }
    }

    /**
     * Update AIOSEO data in its custom table
     */
    private function update_aioseo_data($post_id, $data) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'aioseo_posts';
        
        // Check if table exists
        if ($wpdb->get_var("SHOW TABLES LIKE '$table_name'") != $table_name) {
            return false;
        }

        // Try to find existing record
        $exists = $wpdb->get_var($wpdb->prepare("SELECT id FROM $table_name WHERE post_id = %d", $post_id));
        
        if ($exists) {
            return $wpdb->update($table_name, $data, ['post_id' => $post_id]);
        } else {
            $data['post_id'] = $post_id;
            if (!isset($data['created'])) $data['created'] = current_time('mysql');
            if (!isset($data['updated'])) $data['updated'] = current_time('mysql');
            return $wpdb->insert($table_name, $data);
        }
    }

    /**
     * Update AIOSEO term data in its custom table
     */
    private function update_aioseo_term_data($term_id, $data) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'aioseo_terms';
        
        if ($wpdb->get_var("SHOW TABLES LIKE '$table_name'") != $table_name) {
            return false;
        }

        $exists = $wpdb->get_var($wpdb->prepare("SELECT id FROM $table_name WHERE term_id = %d", $term_id));
        
        if ($exists) {
            return $wpdb->update($table_name, $data, ['term_id' => $term_id]);
        } else {
            $data['term_id'] = $term_id;
            if (!isset($data['created'])) $data['created'] = current_time('mysql');
            if (!isset($data['updated'])) $data['updated'] = current_time('mysql');
            return $wpdb->insert($table_name, $data);
        }
    }
    
    /**
     * Clear various levels of cache
     */
    private function clear_caches($post_id) {
        // WordPress Object Cache
        wp_cache_delete($post_id, 'posts');
        clean_post_cache($post_id);
        
        // Common Caching Plugins
        if (function_exists('w3tc_flush_url')) {
            w3tc_flush_url(get_permalink($post_id));
        }
        if (class_exists('WpFastestCache') && isset($GLOBALS['wp_fastest_cache'])) {
            $GLOBALS['wp_fastest_cache']->deleteCache(false);
        }
        if (function_exists('wp_cache_clean_cache')) {
            global $file_prefix;
            wp_cache_clean_cache($file_prefix);
        }
        
        // Try to clear AIOSEO internal cache if possible
        if (class_exists('AIOSEO\Plugin\Common\Utils\Cache')) {
            try {
                \AIOSEO\Plugin\Common\Utils\Cache::delete('aioseo_post_' . $post_id);
            } catch (\Exception $e) {
                // Ignore
            }
        }
    }
    
    /**
     * Apply AI-powered fix via Python backend
     */
    private function apply_ai_fix($id, $issue_type) {
        if (strpos($id, 'term_') === 0) {
            $term_id = (int)str_replace('term_', '', $id);
            $url = get_term_link($term_id);
        } else {
            $url = get_permalink($id);
        }
        
        // Prepare request to Python backend
        $endpoint = trailingslashit($this->python_engine_url) . 'api/execute-selected';
        
        $response = wp_remote_post($endpoint, [
            'headers' => [
                'Content-Type' => 'application/json',
            ],
            'body' => json_encode([
                'actions' => [
                    [
                        'id' => 'direct_' . $post_id . '_' . time(),
                        'action_type' => 'update',
                        'url' => $url,
                        'issue_type' => $issue_type
                    ]
                ],
                'site_url' => home_url(),
                'wp_username' => $this->username,
                'wp_app_password' => $this->password
            ]),
            'timeout' => 30
        ]);
        
        if (is_wp_error($response)) {
            return [
                'success' => false,
                'message' => 'AI Engine unreachable: ' . $response->get_error_message()
            ];
        }
        
        $body = json_decode(wp_remote_retrieve_body($response), true);
        
        if (isset($body['results'][0]) && $body['results'][0]['success']) {
            $value = $body['results'][0]['value'] ?? '';
            
            // Apply the value locally as well to ensure it persists in the database
            if (strpos($id, 'term_') === 0) {
                $term_id = (int)str_replace('term_', '', $id);
                $type = (strpos($issue_type, 'title') !== false) ? 'title' : 'meta_description';
                $this->update_term_metadata($term_id, $type, $value);
            } else {
                $type = (strpos($issue_type, 'title') !== false) ? 'title' : 'meta_description';
                $this->update_metadata($id, $type, $value);
            }

            return [
                'success' => true,
                'message' => 'Fixed via AI Engine: ' . ($body['results'][0]['message'] ?? 'Success'),
                'value' => $value,
                'reasoning' => $body['results'][0]['reasoning'] ?? ''
            ];
        }
        
        return [
            'success' => false,
            'message' => 'AI Engine failed: ' . ($body['results'][0]['error'] ?? 'Unknown error'),
            'reasoning' => $body['results'][0]['reasoning'] ?? ''
        ];
    }

    /**
     * Generate meta description from content
     */
    private function generate_meta_description($post) {
        // Try excerpt first
        if (!empty($post->post_excerpt)) {
            $description = $post->post_excerpt;
        } else {
            // Extract from content
            $content = wp_strip_all_tags($post->post_content);
            $content = preg_replace('/\s+/', ' ', $content); // Normalize whitespace
            $description = $content;
        }
        
        // Trim to optimal length (120-155 chars)
        if (strlen($description) > 155) {
            $description = substr($description, 0, 152) . '...';
        }
        
        return trim($description);
    }
    
    /**
     * Make API request (for remote sites)
     */
    private function api_request($method, $endpoint, $data = []) {
        $url = trailingslashit($this->site_url) . 'wp-json/' . $endpoint;
        
        if ($method === 'GET' && !empty($data)) {
            $url = add_query_arg($data, $url);
        }
        
        $args = [
            'method' => $method,
            'timeout' => 30,
            'headers' => [
                'Content-Type' => 'application/json',
            ],
        ];
        
        if ($this->username && $this->password) {
            $args['headers']['Authorization'] = 'Basic ' . base64_encode("{$this->username}:{$this->password}");
        }
        
        if ($method !== 'GET' && !empty($data)) {
            $args['body'] = json_encode($data);
        }
        
        $response = wp_remote_request($url, $args);
        
        if (is_wp_error($response)) {
            return $response;
        }
        
        return json_decode(wp_remote_retrieve_body($response), true);
    }
}
