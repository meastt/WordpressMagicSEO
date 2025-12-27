<?php
/**
 * Plugin Name: Magic SEO Connector
 * Plugin URI:  https://example.com/magic-seo
 * Description: Connects your WordPress site to the Magic SEO Vercel automation platform.
 * Version:     1.0.0
 * Author:      Magic SEO Team
 * Author URI:  https://example.com
 * License:     GPL-2.0+
 */

// Prevent direct access
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Magic_SEO_Connector {

    private $option_name = 'magic_seo_options';

    public function __construct() {
        add_action( 'admin_menu', array( $this, 'add_plugin_page' ) );
        add_action( 'admin_init', array( $this, 'page_init' ) );
        add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_styles' ) );
    }

    public function add_plugin_page() {
        add_menu_page(
            'Magic SEO Settings', 
            'Magic SEO', 
            'manage_options', 
            'magic-seo-connector', 
            array( $this, 'create_admin_page' ), 
            'dashicons-chart-line', 
            99
        );
    }

    public function create_admin_page() {
        $this->options = get_option( $this->option_name );
        ?>
        <div class="wrap">
            <h1>Magic SEO Connector</h1>
            <p>Connect this site to your Magic SEO Vercel automation server.</p>
            <form method="post" action="options.php">
                <?php
                // This prints out all hidden setting fields
                settings_fields( 'magic_seo_option_group' );
                do_settings_sections( 'magic-seo-connector' );
                submit_button();
                ?>
            </form>
            
            <hr>
            
            <h2>Usage Info</h2>
            <p><strong>Vercel API URL:</strong> <code id="vercel_url_display">N/A</code></p>
            <p>Use the credentials above when configuring your Vercel automation.</p>
        </div>
        <?php
    }

    public function page_init() {
        register_setting(
            'magic_seo_option_group', // Option group
            $this->option_name, // Option name
            array( $this, 'sanitize' ) // Sanitize
        );

        add_settings_section(
            'setting_section_id', // ID
            'Connection Settings', // Title
            array( $this, 'print_section_info' ), // Callback
            'magic-seo-connector' // Page
        );

        add_settings_field(
            'username', 
            'WordPress Username', 
            array( $this, 'username_callback' ), 
            'magic-seo-connector', 
            'setting_section_id'
        );

        add_settings_field(
            'app_password', 
            'Application Password', 
            array( $this, 'app_password_callback' ), 
            'magic-seo-connector', 
            'setting_section_id'
        );
        
        add_settings_field(
            'vercel_url', 
            'Vercel Server URL', 
            array( $this, 'vercel_url_callback' ), 
            'magic-seo-connector', 
            'setting_section_id'
        );
    }

    public function sanitize( $input ) {
        $new_input = array();
        if( isset( $input['username'] ) )
            $new_input['username'] = sanitize_text_field( $input['username'] );

        if( isset( $input['app_password'] ) )
            $new_input['app_password'] = sanitize_text_field( $input['app_password'] );
            
        if( isset( $input['vercel_url'] ) )
            $new_input['vercel_url'] = esc_url_raw( $input['vercel_url'] );

        return $new_input;
    }

    public function print_section_info() {
        print 'Enter the credentials that the Magic SEO app will use to manage this site.';
        print '<br><i>To generate an Application Password, go to Users > Profile > Application Passwords.</i>';
    }

    public function username_callback() {
        printf(
            '<input type="text" id="username" name="magic_seo_options[username]" value="%s" class="regular-text" />',
            isset( $this->options['username'] ) ? esc_attr( $this->options['username'] ) : ''
        );
    }

    public function app_password_callback() {
        printf(
            '<input type="password" id="app_password" name="magic_seo_options[app_password]" value="%s" class="regular-text" />',
            isset( $this->options['app_password'] ) ? esc_attr( $this->options['app_password'] ) : ''
        );
        print '<br><small>This is stored in your database. Ensure your database is secure.</small>';
    }
    
    public function vercel_url_callback() {
        printf(
            '<input type="url" id="vercel_url" name="magic_seo_options[vercel_url]" value="%s" class="regular-text" placeholder="https://your-app.vercel.app" />',
            isset( $this->options['vercel_url'] ) ? esc_attr( $this->options['vercel_url'] ) : ''
        );
    }
    
    public function enqueue_styles() {
        // Optional: Add custom CSS
    }

}

if( is_admin() )
    $magic_seo_connector = new Magic_SEO_Connector();
