/**
 * auditDataTransformer.js
 * Transforms raw audit JSON from TechnicalSEOAuditor into frontend-friendly format
 * Uses weighted scoring based on SEO impact (from FIX_IMPACT_SCORES)
 */

/**
 * SEO issue impact weights (1-10)
 * Higher = more impactful for rankings
 * Sourced from seo/issue_grouper.py FIX_IMPACT_SCORES
 */
const ISSUE_WEIGHTS = {
    // Critical SEO factors (9-10)
    robots_txt_blocking: 10,
    noindex: 10,
    h1_presence: 9,
    title_presence: 9,
    canonical_tag: 9,

    // High impact (7-8)
    meta_description_presence: 8,
    title_length: 7,
    meta_description_length: 7,
    multiple_h1s: 7,
    mixed_content: 7,

    // Medium impact (5-6)
    schema_markup: 6,
    orphaned_pages: 6,
    open_graph: 5,
    heading_hierarchy: 5,
    image_alt_text: 5,

    // Lower impact (3-4)
    image_dimensions: 4,
    internal_links: 4,
    external_links: 4,
    broken_links: 3,
    anchor_text: 3,
    content_length: 3,
    image_file_size: 3,
    ttfb: 2,
    www_redirect: 2,
    twitter_cards: 2,
    compression: 1
};

// Default weight for unlisted issue types
const DEFAULT_WEIGHT = 3;

/**
 * Transform raw audit data from backend to frontend format
 * @param {Object} rawAudit - Raw audit JSON from TechnicalSEOAuditor
 * @returns {Object} Transformed audit data for frontend
 */
export const transformAuditData = (rawAudit) => {
    const issuesByType = {};
    let criticalCount = 0;
    let warningCount = 0;
    let passedCount = 0;

    // Weighted score tracking
    let totalWeightedPenalty = 0;
    let maxPossibleWeight = 0;

    // Process each URL
    (rawAudit.urls || []).forEach(urlResult => {
        const url = urlResult.url;
        const allIssues = urlResult.issues || {};

        // Flatten all issue categories (technical, onpage, links, images, etc.)
        Object.values(allIssues).forEach(categoryIssues => {
            (categoryIssues || []).forEach(issue => {
                const checkName = issue.check_name;
                const status = issue.status;
                const weight = ISSUE_WEIGHTS[checkName] || DEFAULT_WEIGHT;

                // Track max possible (every check could be critical)
                maxPossibleWeight += weight;

                // Count by status and track weighted penalty
                if (status === 'critical') {
                    criticalCount++;
                    totalWeightedPenalty += weight * 1.0; // Full penalty

                    // Add to issues by type
                    if (!issuesByType[checkName]) {
                        issuesByType[checkName] = [];
                    }
                    issuesByType[checkName].push({
                        url,
                        message: issue.message,
                        severity: issue.severity,
                        value: issue.value,
                        weight
                    });
                } else if (status === 'warning') {
                    warningCount++;
                    totalWeightedPenalty += weight * 0.3; // 30% penalty for warnings

                    // Add to issues by type
                    if (!issuesByType[checkName]) {
                        issuesByType[checkName] = [];
                    }
                    issuesByType[checkName].push({
                        url,
                        message: issue.message,
                        severity: issue.severity,
                        value: issue.value,
                        weight
                    });
                } else if (status === 'optimal') {
                    passedCount++;
                    // No penalty for passed
                }
            });
        });
    });

    // Calculate weighted score (0-100)
    // Score = 100 - (weighted penalty / max possible weight) * 100
    // But we want a reasonable score, so cap the penalty impact
    const penaltyRatio = maxPossibleWeight > 0
        ? totalWeightedPenalty / maxPossibleWeight
        : 0;

    const weightedScore = Math.round(100 - (penaltyRatio * 100));

    return {
        site_url: rawAudit.site_url,
        audit_date: rawAudit.audit_date,
        total_urls_checked: rawAudit.total_urls_checked || (rawAudit.urls || []).length,
        summary: {
            critical_issues: criticalCount,
            warnings: warningCount,
            passed: passedCount,
            weighted_penalty: totalWeightedPenalty,
            max_weight: maxPossibleWeight
        },
        issues_by_type: issuesByType,
        score: weightedScore
    };
};

/**
 * Calculate health score from audit summary using weighted formula
 * 
 * @param {Object} summary - { critical_issues, warnings, passed, weighted_penalty, max_weight }
 * @returns {number} Score 0-100
 */
export const calculateHealthScore = (summary) => {
    if (!summary) return 0;

    const { critical_issues = 0, warnings = 0, passed = 0 } = summary;
    const totalChecks = critical_issues + warnings + passed;

    if (totalChecks === 0) return 100;

    // If we have pre-calculated weighted values, use them
    if (summary.weighted_penalty !== undefined && summary.max_weight > 0) {
        const penaltyRatio = summary.weighted_penalty / summary.max_weight;
        return Math.max(0, Math.min(100, Math.round(100 - (penaltyRatio * 100))));
    }

    // Fallback: Simple pass rate with light penalties
    // This is less accurate but works if weighted data isn't available
    const passRate = passed / totalChecks;
    const criticalPenalty = Math.min(30, critical_issues * 0.5);
    const warningPenalty = Math.min(15, warnings * 0.1);

    const score = Math.round((passRate * 100) - criticalPenalty - warningPenalty);

    return Math.max(0, Math.min(100, score));
};

/**
 * Get friendly name for issue type
 */
export const getIssueTypeName = (issueType) => {
    const names = {
        h1_presence: 'Missing H1',
        title_presence: 'Missing Title',
        title_length: 'Title Length',
        meta_description_presence: 'Missing Description',
        meta_description_length: 'Description Length',
        heading_hierarchy: 'Heading Issues',
        multiple_h1s: 'Multiple H1s',
        schema_markup: 'Schema',
        open_graph: 'Open Graph',
        twitter_cards: 'Twitter Cards',
        image_alt_text: 'Image Alt Text',
        image_dimensions: 'Image Dimensions',
        image_file_size: 'Large Images',
        internal_links: 'Internal Links',
        external_links: 'External Links',
        broken_links: 'Broken Links',
        anchor_text: 'Anchor Text',
        mixed_content: 'Mixed Content',
        robots_txt: 'Robots.txt',
        noindex: 'No-Index',
        canonical_tag: 'Canonical',
        www_redirect: 'WWW Redirect',
        ttfb: 'Slow TTFB',
        content_length: 'Thin Content',
        compression: 'Compression',
        ssl_https: 'SSL/HTTPS'
    };
    return names[issueType] || issueType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

/**
 * Get issue weight for sorting tabs by impact
 */
export const getIssueWeight = (issueType) => {
    return ISSUE_WEIGHTS[issueType] || DEFAULT_WEIGHT;
};

export default { transformAuditData, calculateHealthScore, getIssueTypeName, getIssueWeight };
