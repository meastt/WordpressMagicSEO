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
    
    /**
     * Constructor
     */
    public function __construct($site_url = null, $username = null, $password = null) {
        $this->site_url = $site_url ?: home_url();
        $this->username = $username;
        $this->password = $password;
    }
    
    /**
     * Get post ID from URL
     */
    public function get_post_id_from_url($url) {
        // Try using url_to_postid (works for local site)
        $post_id = url_to_postid($url);
        
        if ($post_id) {
            return $post_id;
        }
        
        // For remote sites, query via REST API
        if ($this->site_url !== home_url()) {
            $response = $this->api_request('GET', 'wp/v2/posts', [
                'slug' => basename(parse_url($url, PHP_URL_PATH)),
            ]);
            
            if (!is_wp_error($response) && !empty($response)) {
                return $response[0]['id'] ?? null;
            }
        }
        
        return null;
    }
    
    /**
     * Fix missing/short title
     */
    public function fix_title($post_id, $new_title = null) {
        $post = get_post($post_id);
        if (!$post) {
            return [
                'success' => false,
                'message' => 'Post not found',
            ];
        }
        
        // Generate title if not provided
        if (empty($new_title)) {
            $new_title = $this->generate_seo_title($post);
        }
        
        // Try Yoast first
        if ($this->has_yoast()) {
            update_post_meta($post_id, '_yoast_wpseo_title', $new_title);
            return [
                'success' => true,
                'message' => 'Title updated via Yoast',
                'value' => $new_title,
            ];
        }
        
        // Try RankMath
        if ($this->has_rankmath()) {
            update_post_meta($post_id, 'rank_math_title', $new_title);
            return [
                'success' => true,
                'message' => 'Title updated via RankMath',
                'value' => $new_title,
            ];
        }
        
        // Try AIOSEO
        if ($this->has_aioseo()) {
            update_post_meta($post_id, '_aioseo_title', $new_title);
            return [
                'success' => true,
                'message' => 'Title updated via AIOSEO',
                'value' => $new_title,
            ];
        }
        
        // Fallback: Update post title directly
        wp_update_post([
            'ID' => $post_id,
            'post_title' => $new_title,
        ]);
        
        return [
            'success' => true,
            'message' => 'Post title updated',
            'value' => $new_title,
        ];
    }
    
    /**
     * Fix missing/short meta description
     */
    public function fix_meta_description($post_id, $description = null) {
        $post = get_post($post_id);
        if (!$post) {
            return [
                'success' => false,
                'message' => 'Post not found',
            ];
        }
        
        // Generate description if not provided
        if (empty($description)) {
            $description = $this->generate_meta_description($post);
        }
        
        // Try Yoast first
        if ($this->has_yoast()) {
            update_post_meta($post_id, '_yoast_wpseo_metadesc', $description);
            return [
                'success' => true,
                'message' => 'Meta description updated via Yoast',
                'value' => $description,
            ];
        }
        
        // Try RankMath
        if ($this->has_rankmath()) {
            update_post_meta($post_id, 'rank_math_description', $description);
            return [
                'success' => true,
                'message' => 'Meta description updated via RankMath',
                'value' => $description,
            ];
        }
        
        // Try AIOSEO
        if ($this->has_aioseo()) {
            update_post_meta($post_id, '_aioseo_description', $description);
            return [
                'success' => true,
                'message' => 'Meta description updated via AIOSEO',
                'value' => $description,
            ];
        }
        
        // Fallback: Store in post excerpt
        wp_update_post([
            'ID' => $post_id,
            'post_excerpt' => $description,
        ]);
        
        return [
            'success' => true,
            'message' => 'Meta description stored in excerpt',
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
                    $result = $this->fix_title($post_id);
                    break;
                    
                case 'meta_description_presence':
                case 'meta_description_length':
                    $result = $this->fix_meta_description($post_id);
                    break;
                    
                case 'h1_presence':
                    $result = $this->fix_h1($post_id);
                    break;
                    
                case 'multiple_h1s':
                    $result = $this->fix_multiple_h1s($post_id);
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
    
    /**
     * Generate SEO-optimized title
     */
    private function generate_seo_title($post) {
        $title = $post->post_title;
        $site_name = get_bloginfo('name');
        
        // Ensure title is within optimal length (30-60 chars)
        if (strlen($title) < 30) {
            // Append site name if room
            $with_site = "{$title} | {$site_name}";
            if (strlen($with_site) <= 60) {
                return $with_site;
            }
        }
        
        if (strlen($title) > 60) {
            // Truncate and add ellipsis
            return substr($title, 0, 57) . '...';
        }
        
        return $title;
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
