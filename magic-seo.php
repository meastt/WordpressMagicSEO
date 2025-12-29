<?php
/**
 * Plugin Name: Magic SEO
 * Plugin URI: https://github.com/magicseo
 * Description: AI-powered SEO content optimization with Claude, Gemini, and advanced affiliate management.
 * Version: 1.1.16
 * Author: Magic SEO
 * Author URI: https://magicseo.com
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: magic-seo
 * Requires at least: 6.0
 * Requires PHP: 7.4
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Plugin constants
define('MAGIC_SEO_VERSION', '1.1.16');
define('MAGIC_SEO_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('MAGIC_SEO_PLUGIN_URL', plugin_dir_url(__FILE__));

// Include classes
require_once MAGIC_SEO_PLUGIN_DIR . 'includes/class-seo-auditor.php';
require_once MAGIC_SEO_PLUGIN_DIR . 'includes/class-seo-fixer.php';

/**
 * Main plugin class
 */
class MagicSEO {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        add_action('admin_menu', [$this, 'register_admin_menu']);
        add_action('admin_enqueue_scripts', [$this, 'enqueue_admin_scripts']);
        add_action('rest_api_init', [$this, 'register_rest_routes']);
    }
    
    /**
     * Register admin menu
     */
    public function register_admin_menu() {
        add_menu_page(
            __('Magic SEO', 'magic-seo'),
            __('Magic SEO', 'magic-seo'),
            'manage_options',
            'magic-seo',
            [$this, 'render_admin_page'],
            'dashicons-superhero',
            30
        );
    }
    
    /**
     * Render admin page
     */
    public function render_admin_page() {
        ?>
        <div class="wrap magic-seo-wrap">
            <div class="magic-seo-dashboard">
                <div id="magic-seo-root"></div>
            </div>
        </div>
        <?php
    }
    
    /**
     * Enqueue admin scripts and styles
     */
    public function enqueue_admin_scripts($hook) {
        if ($hook !== 'toplevel_page_magic-seo') {
            return;
        }
        
        // Dequeue WordPress media scripts that conflict with our React app
        // These cause "_.isArray is not a function" errors
        wp_dequeue_script('media-editor');
        wp_dequeue_script('media-views');
        wp_dequeue_script('media-models');
        wp_dequeue_script('wp-backbone');
        wp_dequeue_script('media-audiovideo');
        wp_dequeue_script('mce-view');
        
        // Google Fonts
        wp_enqueue_style(
            'magic-seo-fonts',
            'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Caveat:wght@400;500;600&display=swap',
            [],
            null
        );
        
        // Main CSS - use timestamp for cache busting
        $cache_bust = MAGIC_SEO_VERSION . '.' . filemtime(MAGIC_SEO_PLUGIN_DIR . 'build/app.css');
        wp_enqueue_style(
            'magic-seo-styles',
            MAGIC_SEO_PLUGIN_URL . 'build/app.css',
            [],
            $cache_bust
        );
        
        // Main JS - use timestamp for cache busting
        $js_cache_bust = MAGIC_SEO_VERSION . '.' . filemtime(MAGIC_SEO_PLUGIN_DIR . 'build/app.js');
        wp_enqueue_script(
            'magic-seo-app',
            MAGIC_SEO_PLUGIN_URL . 'build/app.js',
            ['wp-element', 'wp-api-fetch'],
            $js_cache_bust,
            true
        );
        
        // Localize script with API data
        wp_localize_script('magic-seo-app', 'magicSeoData', [
            'apiUrl' => rest_url('magic-seo/v1/'),
            'nonce' => wp_create_nonce('wp_rest'),
            'pluginUrl' => MAGIC_SEO_PLUGIN_URL,
            'version' => MAGIC_SEO_VERSION
        ]);
    }
    
    /**
     * Register REST API routes
     */
    public function register_rest_routes() {
        // Settings endpoints
        register_rest_route('magic-seo/v1', '/settings', [
            'methods' => 'GET',
            'callback' => [$this, 'get_settings'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        register_rest_route('magic-seo/v1', '/settings', [
            'methods' => 'POST',
            'callback' => [$this, 'save_settings'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        // Affiliates endpoints
        register_rest_route('magic-seo/v1', '/affiliates', [
            'methods' => 'GET',
            'callback' => [$this, 'get_affiliates'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        register_rest_route('magic-seo/v1', '/affiliates', [
            'methods' => 'POST',
            'callback' => [$this, 'save_affiliates'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        // Test connection endpoint
        register_rest_route('magic-seo/v1', '/test-connection', [
            'methods' => 'POST',
            'callback' => [$this, 'test_connection'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        // Link checker endpoint
        register_rest_route('magic-seo/v1', '/check-links', [
            'methods' => 'POST',
            'callback' => [$this, 'check_links'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        // Optimize endpoint
        register_rest_route('magic-seo/v1', '/optimize', [
            'methods' => 'POST',
            'callback' => [$this, 'run_optimization'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        // Audit endpoints
        register_rest_route('magic-seo/v1', '/audit/start', [
            'methods' => 'POST',
            'callback' => [$this, 'start_audit'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        register_rest_route('magic-seo/v1', '/audit/status', [
            'methods' => 'GET',
            'callback' => [$this, 'get_audit_status'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        register_rest_route('magic-seo/v1', '/audit/results', [
            'methods' => 'GET',
            'callback' => [$this, 'get_audit_results'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
        
        // Fix endpoint
        register_rest_route('magic-seo/v1', '/fix/batch', [
            'methods' => 'POST',
            'callback' => [$this, 'fix_batch'],
            'permission_callback' => [$this, 'check_admin_permission']
        ]);
    }
    
    /**
     * Check admin permission
     */
    public function check_admin_permission() {
        return current_user_can('manage_options');
    }
    
    /**
     * Get settings
     */
    public function get_settings() {
        $settings = get_option('magic_seo_settings', []);
        
        // Mask sensitive keys for frontend
        $masked = $settings;
        if (!empty($masked['anthropic_key'])) {
            $masked['anthropic_key'] = $this->mask_key($masked['anthropic_key']);
        }
        if (!empty($masked['gemini_key'])) {
            $masked['gemini_key'] = $this->mask_key($masked['gemini_key']);
        }
        if (!empty($masked['openai_key'])) {
            $masked['openai_key'] = $this->mask_key($masked['openai_key']);
        }
        
        if (empty($masked['python_engine_url'])) {
            $masked['python_engine_url'] = 'http://localhost:5000';
        }
        
        return rest_ensure_response($masked);
    }
    
    /**
     * Save settings
     */
    public function save_settings($request) {
        $params = $request->get_json_params();
        
        // Encrypt sensitive data before saving
        $settings = [
            'anthropic_key' => $this->encrypt_value($params['anthropic_key'] ?? ''),
            'gemini_key' => $this->encrypt_value($params['gemini_key'] ?? ''),
            'openai_key' => $this->encrypt_value($params['openai_key'] ?? ''),
            'sites' => array_map(function($site) {
                return [
                    'site_url' => sanitize_url($site['site_url'] ?? ''),
                    'username' => sanitize_text_field($site['username'] ?? ''),
                    'app_password' => $this->encrypt_value($site['app_password'] ?? '')
                ];
            }, $params['sites'] ?? []),
            'python_engine_url' => sanitize_url($params['python_engine_url'] ?? 'http://localhost:5000'),
            'use_ai_fixes' => (bool) ($params['use_ai_fixes'] ?? true)
        ];
        
        update_option('magic_seo_settings', $settings);
        
        return rest_ensure_response(['success' => true]);
    }
    
    /**
     * Get affiliates
     */
    public function get_affiliates() {
        $affiliates = get_option('magic_seo_affiliates', []);
        return rest_ensure_response($affiliates);
    }
    
    /**
     * Save affiliates
     */
    public function save_affiliates($request) {
        $params = $request->get_json_params();
        
        $affiliates = array_map(function($network) {
            return [
                'id' => sanitize_text_field($network['id'] ?? ''),
                'name' => sanitize_text_field($network['name'] ?? ''),
                'icon' => sanitize_text_field($network['icon'] ?? ''),
                'urlPattern' => sanitize_text_field($network['urlPattern'] ?? ''),
                'paramName' => sanitize_text_field($network['paramName'] ?? ''),
                'affiliateId' => sanitize_text_field($network['affiliateId'] ?? ''),
                'enabled' => (bool) ($network['enabled'] ?? false)
            ];
        }, $params);
        
        update_option('magic_seo_affiliates', $affiliates);
        
        return rest_ensure_response(['success' => true]);
    }
    
    /**
     * Test connection to API
     */
    public function test_connection($request) {
        $params = $request->get_json_params();
        $type = $params['type'] ?? '';
        $key = $params['key'] ?? '';
        
        switch ($type) {
            case 'anthropic':
                $result = $this->test_anthropic_connection($key);
                break;
            case 'gemini':
                $result = $this->test_gemini_connection($key);
                break;
            case 'wordpress':
                $result = $this->test_wordpress_connection(
                    $params['site_url'] ?? '',
                    $params['username'] ?? '',
                    $params['app_password'] ?? ''
                );
                break;
            default:
                $result = ['success' => false, 'message' => 'Unknown connection type'];
        }
        
        return rest_ensure_response($result);
    }
    
    /**
     * Check links in URLs
     */
    public function check_links($request) {
        $params = $request->get_json_params();
        $urls = $params['urls'] ?? [];
        
        $results = [];
        foreach ($urls as $url) {
            $results[] = $this->analyze_post_links($url);
        }
        
        return rest_ensure_response($results);
    }
    
    /**
     * Run optimization
     */
    public function run_optimization($request) {
        $params = $request->get_json_params();
        
        // TODO: Integrate with Python backend or implement in PHP
        return rest_ensure_response([
            'success' => true,
            'message' => 'Optimization queued',
            'job_id' => uniqid('opt_')
        ]);
    }
    
    /**
     * Start SEO audit
     */
    public function start_audit($request) {
        $params = $request->get_json_params();
        $site_url = $params['site_url'] ?? home_url();
        $max_urls = $params['max_urls'] ?? null;
        
        // Mark audit as running
        update_option('magic_seo_audit_status', [
            'status' => 'running',
            'site_url' => $site_url,
            'started_at' => current_time('c'),
            'progress' => 0,
            'current_url' => '',
            'total_urls' => 0,
        ]);
        
        // Run audit (this runs synchronously - for large sites consider background processing)
        $auditor = new Magic_SEO_Auditor();
        
        // Progress callback to update status
        $progress_callback = function($progress) {
            $status = get_option('magic_seo_audit_status', []);
            $status['progress'] = $progress['percent'];
            $status['current_url'] = $progress['url'];
            $status['total_urls'] = $progress['total'];
            $status['urls_scanned'] = $progress['current'];
            update_option('magic_seo_audit_status', $status);
        };
        
        try {
            $results = $auditor->audit_site($site_url, $max_urls, $progress_callback);
            
            // Store results
            update_option('magic_seo_audit_results', $results);
            update_option('magic_seo_audit_status', [
                'status' => 'complete',
                'site_url' => $site_url,
                'completed_at' => current_time('c'),
                'progress' => 100,
                'total_urls' => $results['total_urls_checked'],
            ]);
            
            return rest_ensure_response([
                'success' => true,
                'message' => 'Audit complete',
                'total_urls' => $results['total_urls_checked'],
            ]);
            
        } catch (Exception $e) {
            update_option('magic_seo_audit_status', [
                'status' => 'error',
                'error' => $e->getMessage(),
            ]);
            
            return rest_ensure_response([
                'success' => false,
                'message' => $e->getMessage(),
            ]);
        }
    }
    
    /**
     * Get audit status
     */
    public function get_audit_status() {
        $status = get_option('magic_seo_audit_status', [
            'status' => 'idle',
        ]);
        
        return rest_ensure_response($status);
    }
    
    /**
     * Get audit results
     */
    public function get_audit_results() {
        $results = get_option('magic_seo_audit_results', null);
        
        if (!$results) {
            return rest_ensure_response([
                'error' => 'No audit results found. Run an audit first.',
            ]);
        }
        
        return rest_ensure_response($results);
    }
    
    /**
     * Fix batch of issues
     */
    public function fix_batch($request) {
        $params = $request->get_json_params();
        $issue_type = $params['issue_type'] ?? '';
        $urls = $params['urls'] ?? [];
        
        if (empty($issue_type) || empty($urls)) {
            return rest_ensure_response([
                'success' => false,
                'message' => 'Missing issue_type or urls',
            ]);
        }
        
        $fixer = new Magic_SEO_Fixer();
        $results = $fixer->fix_batch($issue_type, $urls);
        
        return rest_ensure_response([
            'success' => true,
            'results' => $results,
        ]);
    }
    
    // Helper methods
    
    private function mask_key($key) {
        if (strlen($key) <= 8) {
            return str_repeat('•', strlen($key));
        }
        return substr($key, 0, 4) . str_repeat('•', strlen($key) - 8) . substr($key, -4);
    }
    
    private function encrypt_value($value) {
        if (empty($value)) return '';
        $key = wp_salt('auth');
        $iv = substr(hash('sha256', wp_salt('secure_auth')), 0, 16);
        return base64_encode(openssl_encrypt($value, 'AES-256-CBC', $key, 0, $iv));
    }
    
    private function decrypt_value($encrypted) {
        if (empty($encrypted)) return '';
        $key = wp_salt('auth');
        $iv = substr(hash('sha256', wp_salt('secure_auth')), 0, 16);
        return openssl_decrypt(base64_decode($encrypted), 'AES-256-CBC', $key, 0, $iv);
    }
    
    private function test_anthropic_connection($key) {
        $response = wp_remote_get('https://api.anthropic.com/v1/models', [
            'headers' => [
                'x-api-key' => $key,
                'anthropic-version' => '2023-06-01'
            ],
            'timeout' => 10
        ]);
        
        if (is_wp_error($response)) {
            return ['success' => false, 'message' => $response->get_error_message()];
        }
        
        $code = wp_remote_retrieve_response_code($response);
        return [
            'success' => $code === 200,
            'message' => $code === 200 ? 'Connected!' : 'Invalid API key'
        ];
    }
    
    private function test_gemini_connection($key) {
        $response = wp_remote_get("https://generativelanguage.googleapis.com/v1beta/models?key={$key}", [
            'timeout' => 10
        ]);
        
        if (is_wp_error($response)) {
            return ['success' => false, 'message' => $response->get_error_message()];
        }
        
        $code = wp_remote_retrieve_response_code($response);
        return [
            'success' => $code === 200,
            'message' => $code === 200 ? 'Connected!' : 'Invalid API key'
        ];
    }
    
    private function test_wordpress_connection($site_url, $username, $password) {
        $response = wp_remote_get(trailingslashit($site_url) . 'wp-json/wp/v2/users/me', [
            'headers' => [
                'Authorization' => 'Basic ' . base64_encode("{$username}:{$password}")
            ],
            'timeout' => 10
        ]);
        
        if (is_wp_error($response)) {
            return ['success' => false, 'message' => $response->get_error_message()];
        }
        
        $code = wp_remote_retrieve_response_code($response);
        return [
            'success' => $code === 200,
            'message' => $code === 200 ? 'Connected!' : 'Invalid credentials'
        ];
    }
    
    private function analyze_post_links($url) {
        // Fetch the page content
        $response = wp_remote_get($url, ['timeout' => 15]);
        
        if (is_wp_error($response)) {
            return ['url' => $url, 'error' => $response->get_error_message()];
        }
        
        $html = wp_remote_retrieve_body($response);
        $links = [];
        
        // Extract links using regex (simple approach)
        preg_match_all('/<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)<\/a>/i', $html, $matches, PREG_SET_ORDER);
        
        foreach ($matches as $match) {
            $href = $match[1];
            $text = $match[2];
            
            // Skip internal links
            if (strpos($href, parse_url($url, PHP_URL_HOST)) !== false) {
                continue;
            }
            
            // Skip non-http links
            if (strpos($href, 'http') !== 0) {
                continue;
            }
            
            $links[] = [
                'url' => $href,
                'anchor' => $text,
                'status' => $this->check_link_status($href)
            ];
        }
        
        return ['url' => $url, 'links' => $links];
    }
    
    private function check_link_status($url) {
        $response = wp_remote_head($url, ['timeout' => 5, 'redirection' => 3]);
        
        if (is_wp_error($response)) {
            return ['valid' => false, 'code' => 0, 'error' => $response->get_error_message()];
        }
        
        $code = wp_remote_retrieve_response_code($response);
        return [
            'valid' => $code >= 200 && $code < 400,
            'code' => $code
        ];
    }
}

// Initialize plugin
function magic_seo_init() {
    MagicSEO::get_instance();
}
add_action('plugins_loaded', 'magic_seo_init');

// Activation hook
register_activation_hook(__FILE__, function() {
    // Set default options if not exist
    if (!get_option('magic_seo_settings')) {
        add_option('magic_seo_settings', []);
    }
    if (!get_option('magic_seo_affiliates')) {
        add_option('magic_seo_affiliates', []);
    }
});

// Deactivation hook
register_deactivation_hook(__FILE__, function() {
    // Clean up audit data on deactivation (allows fresh start)
    delete_option('magic_seo_audit_status');
    delete_option('magic_seo_audit_results');
    // Keep settings and affiliates so user doesn't lose API keys
});
