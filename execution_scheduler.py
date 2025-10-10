"""
execution_scheduler.py
=====================
Manages the execution of the action plan with scheduling and rate limiting.
"""

import time
from typing import List, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass
import csv
from strategic_planner import ActionItem, ActionType
from wordpress_publisher import WordPressPublisher, PublishResult
from claude_content_generator import ClaudeContentGenerator


@dataclass
class ScheduleConfig:
    """Configuration for execution scheduling."""
    mode: str  # "all_at_once", "daily", "hourly", "custom"
    posts_per_batch: int = 1
    delay_between_batches: float = 3600.0  # seconds (1 hour default)
    max_api_calls_per_minute: int = 10


class ExecutionScheduler:
    """Orchestrates the execution of the entire content plan."""

    def __init__(
        self,
        action_plan: List[ActionItem],
        wp_publisher: WordPressPublisher,
        content_generator: ClaudeContentGenerator,
        schedule_config: ScheduleConfig,
        planner=None,
        state_manager=None
    ):
        self.action_plan = action_plan
        self.wp_publisher = wp_publisher
        self.content_generator = content_generator
        self.config = schedule_config
        self.planner = planner
        self.state_manager = state_manager
        self.results: List[PublishResult] = []
        self.api_call_count = 0
        self.api_call_reset_time = time.time() + 60
    
    def execute_plan(self, max_actions: int = None) -> List[PublishResult]:
        """Execute the action plan according to schedule configuration."""
        
        actions_to_execute = self.action_plan
        if max_actions:
            actions_to_execute = actions_to_execute[:max_actions]
        
        print(f"\n🚀 Starting execution of {len(actions_to_execute)} actions")
        print(f"Schedule mode: {self.config.mode}")
        
        if self.config.mode == "all_at_once":
            print("⚡ All actions will be processed continuously (no batching)\n")
            return self._execute_all_at_once(actions_to_execute)
        else:
            print(f"Posts per batch: {self.config.posts_per_batch}")
            print(f"Delay between batches: {self.config.delay_between_batches/3600:.1f} hours\n")
            return self._execute_batched(actions_to_execute)
    
    def _execute_all_at_once(self, actions: List[ActionItem]) -> List[PublishResult]:
        """Execute all actions as fast as rate limits allow."""
        for i, action in enumerate(actions, 1):
            print(f"\n{'='*80}")
            print(f"[{i}/{len(actions)}] Processing: {action.action_type.value.upper()}")
            print(f"{'='*80}")

            result = self._execute_action(action)
            self.results.append(result)

            # Mark as completed in state tracker (use StateManager if available)
            if result.success:
                if self.state_manager and hasattr(action, 'id'):
                    # Use StateManager for persistent tracking
                    self.state_manager.mark_completed(action.id, result.post_id)
                elif self.planner:
                    # Fallback to legacy planner
                    self.planner.mark_completed(
                        url=action.url or result.url,
                        action_type=action.action_type.value,
                        post_id=result.post_id
                    )

            # Detailed status update
            if result.success:
                print(f"\n✅ SUCCESS - {action.action_type.value.upper()}")
                print(f"   URL: {result.url}")
                if result.post_id:
                    print(f"   Post ID: {result.post_id}")
                if hasattr(action, 'id'):
                    print(f"   Action ID: {action.id} (marked complete)")
            else:
                print(f"\n❌ FAILED - {action.action_type.value.upper()}")
                print(f"   URL: {action.url}")
                print(f"   Error: {result.error}")

        return self.results
    
    def _execute_batched(self, actions: List[ActionItem]) -> List[PublishResult]:
        """Execute actions in batches with delays."""
        batch_size = self.config.posts_per_batch
        total_batches = (len(actions) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(actions))
            batch = actions[start_idx:end_idx]
            
            print(f"\n📦 Batch {batch_num + 1}/{total_batches}")
            
            for action in batch:
                result = self._execute_action(action)
                self.results.append(result)

                # Mark as completed in state tracker (use StateManager if available)
                if result.success:
                    if self.state_manager and hasattr(action, 'id'):
                        # Use StateManager for persistent tracking
                        self.state_manager.mark_completed(action.id, result.post_id)
                    elif self.planner:
                        # Fallback to legacy planner
                        self.planner.mark_completed(
                            url=action.url or result.url,
                            action_type=action.action_type.value,
                            post_id=result.post_id
                        )

                status = "✅" if result.success else "❌"
                print(f"  {status} {action.action_type.value}: {result.url or action.url}")
            
            # Wait before next batch (unless it's the last batch)
            if batch_num < total_batches - 1:
                wait_time = self.config.delay_between_batches
                print(f"\n⏳ Waiting {wait_time/60:.1f} minutes before next batch...")
                time.sleep(wait_time)
        
        return self.results
    
    def _execute_action(self, action: ActionItem) -> PublishResult:
        """Execute a single action item."""
        
        try:
            if action.action_type == ActionType.DELETE:
                return self._handle_delete(action)
            
            elif action.action_type == ActionType.REDIRECT_301:
                return self._handle_redirect(action)
            
            elif action.action_type == ActionType.UPDATE:
                return self._handle_update(action)
            
            elif action.action_type == ActionType.CREATE:
                return self._handle_create(action)
            
            else:
                return PublishResult(
                    success=False,
                    action="unknown",
                    url=action.url,
                    error=f"Unknown action type: {action.action_type}"
                )
        
        except Exception as e:
            return PublishResult(
                success=False,
                action=action.action_type.value,
                url=action.url,
                error=str(e)
            )
    
    def _handle_delete(self, action: ActionItem) -> PublishResult:
        """Handle DELETE action."""
        # Find the post by URL
        post = self.wp_publisher.find_post_by_url(action.url)
        
        if not post:
            return PublishResult(
                success=False,
                action="delete",
                url=action.url,
                error="Post not found"
            )
        
        # Delete the post
        return self.wp_publisher.delete_post(post['id'], force=True)
    
    def _handle_redirect(self, action: ActionItem) -> PublishResult:
        """Handle 301 REDIRECT action."""
        # First delete the old post
        post = self.wp_publisher.find_post_by_url(action.url)
        if post:
            self.wp_publisher.delete_post(post['id'], force=True)
        
        # Then create the redirect
        return self.wp_publisher.create_301_redirect(
            action.url,
            action.redirect_target
        )
    
    def _handle_update(self, action: ActionItem) -> PublishResult:
        """Handle UPDATE action - refresh existing content."""

        # Find the existing post
        post = self.wp_publisher.find_post_by_url(action.url)
        if not post:
            return PublishResult(
                success=False,
                action="update",
                url=action.url,
                error="Post not found"
            )

        old_title = post['title']['rendered']
        print(f"\n📰 UPDATING POST")
        print(f"   Old Title: {old_title}")
        print(f"   URL: {action.url}")
        print(f"   Post ID: {post['id']}")

        print(f"\n📝 Researching: {action.keywords[0] if action.keywords else old_title}")

        # Research the topic
        self._check_rate_limit()
        research = self.content_generator.research_topic(
            old_title,
            action.keywords
        )

        # Get internal link suggestions
        internal_links = self.wp_publisher.get_internal_link_suggestions(
            action.keywords
        )

        print(f"✍️  Generating updated content with Claude...")

        # Generate updated content with fresh title, content, and taxonomies
        self._check_rate_limit()
        article_data = self.content_generator.generate_article(
            topic_title=old_title,
            keywords=action.keywords,
            research=research,
            meta_description="",  # Will be generated by Claude
            existing_content=post['content']['rendered'],
            internal_links=internal_links
        )

        new_title = article_data.get('title', old_title)
        print(f"\n📝 CHANGES:")
        print(f"   New Title: {new_title}")
        print(f"   Categories: {', '.join(article_data.get('categories', []))}")
        print(f"   Tags: {', '.join(article_data.get('tags', []))}")
        print(f"   Content Length: {len(article_data.get('content', ''))} chars")

        # Update the post with new title, content, meta, and taxonomies
        return self.wp_publisher.update_post(
            post_id=post['id'],
            title=new_title,  # NEW: Update the title
            content=article_data['content'],
            meta_title=article_data.get('meta_title'),
            meta_description=article_data.get('meta_description'),
            categories=article_data.get('categories'),
            tags=article_data.get('tags')
        )
    
    def _handle_create(self, action: ActionItem) -> PublishResult:
        """Handle CREATE action - write new content."""

        print(f"\n📝 CREATING NEW POST")
        print(f"   Topic: {action.title}")
        print(f"   Keywords: {', '.join(action.keywords[:5])}")

        print(f"\n🔍 Researching topic with Claude...")

        # Research the topic
        self._check_rate_limit()
        research = self.content_generator.research_topic(
            action.title,
            action.keywords
        )

        # Get internal link suggestions
        internal_links = self.wp_publisher.get_internal_link_suggestions(
            action.keywords
        )

        print(f"✍️  Generating new article with Claude...")

        # Generate new content
        self._check_rate_limit()
        article_data = self.content_generator.generate_article(
            topic_title=action.title,
            keywords=action.keywords,
            research=research,
            meta_description="",  # Will be generated by Claude
            internal_links=internal_links
        )

        print(f"\n📝 NEW ARTICLE:")
        print(f"   Title: {article_data.get('title', 'N/A')}")
        print(f"   Categories: {', '.join(article_data.get('categories', []))}")
        print(f"   Tags: {', '.join(article_data.get('tags', []))}")
        print(f"   Content Length: {len(article_data.get('content', ''))} chars")

        # Create the post
        return self.wp_publisher.create_post(
            title=article_data['title'],
            content=article_data['content'],
            meta_title=article_data.get('meta_title'),
            meta_description=article_data.get('meta_description'),
            categories=article_data.get('categories'),
            tags=article_data.get('tags'),
            status="publish"
        )
    
    def _check_rate_limit(self):
        """Check and enforce API rate limits."""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time >= self.api_call_reset_time:
            self.api_call_count = 0
            self.api_call_reset_time = current_time + 60
        
        # Check if we've hit the limit
        if self.api_call_count >= self.config.max_api_calls_per_minute:
            wait_time = self.api_call_reset_time - current_time
            if wait_time > 0:
                print(f"  ⏸️  Rate limit reached, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.api_call_count = 0
                self.api_call_reset_time = time.time() + 60
        
        self.api_call_count += 1
        
        # Small delay between API calls
        time.sleep(1)
    
    def save_results_to_csv(self, output_path: str):
        """Save execution results to a CSV tracking file."""
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Headers
            writer.writerow([
                'Timestamp',
                'Action',
                'Status',
                'URL',
                'Post ID',
                'Error'
            ])
            
            # Data rows
            for result in self.results:
                writer.writerow([
                    result.timestamp,
                    result.action,
                    'SUCCESS' if result.success else 'FAILED',
                    result.url,
                    result.post_id or '',
                    result.error or ''
                ])
        
        print(f"\n📊 Results saved to: {output_path}")
    
    def get_summary(self) -> Dict:
        """Get execution summary statistics."""
        total = len(self.results)
        successful = len([r for r in self.results if r.success])
        failed = len([r for r in self.results if not r.success])
        
        actions_count = {}
        for result in self.results:
            action = result.action
            actions_count[action] = actions_count.get(action, 0) + 1
        
        return {
            'total_actions': total,
            'successful': successful,
            'failed': failed,
            'success_rate': f"{(successful/total*100):.1f}%" if total > 0 else "0%",
            'by_action_type': actions_count
        }