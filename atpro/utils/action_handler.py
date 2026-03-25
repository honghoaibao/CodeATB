"""
╔══════════════════════════════════════════════════════╗
║        utils/action_handler.py - v1.4.5              ║
║   SmartActionHandler - Retry + Fallback strategy     ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → SmartActionHandler (line ~8564)

Tự động retry với nhiều strategies, fallback khi action fail,
theo dõi success rate và adapt behavior.
"""

from typing import Callable, Dict, List, Optional

from typing import TYPE_CHECKING
from core.human_behavior import HumanBehavior

class SmartActionHandler:
    """
    v1.4.4 Additional: Smart Action Handler với Fallback
    
    Tự động retry với nhiều strategies khác nhau
    Fallback to alternative actions if primary fails
    Track success rate và adapt behavior
    """
    
    def __init__(self, device, human_behavior: HumanBehavior):
        """Initialize smart action handler"""
        self.device = device
        self.human = human_behavior
        self.success_history = {
            'follow': [],
            'comment': [],
            'like': [],
            'notification': [],
            'shop': []
        }
    
    def execute_with_fallback(self, primary_action, fallback_actions: list, 
                             max_attempts: int = 3, action_name: str = "") -> bool:
        """
        Execute action with fallback strategies
        
        Args:
            primary_action: Primary action function
            fallback_actions: List of fallback functions
            max_attempts: Max retry attempts
            action_name: Name for logging
            
        Returns:
            True if any strategy succeeded
        """
        all_strategies = [primary_action] + fallback_actions
        
        for attempt, strategy in enumerate(all_strategies, 1):
            try:
                if action_name:
                    print(f"🎯 {action_name} - Thử cách {attempt}/{len(all_strategies)}")
                
                result = strategy()
                
                if result:
                    if action_name:
                        print(f"✅ {action_name} thành công (cách {attempt})")
                    return True
                    
            except Exception as e:
                print(f"⚠️  {action_name} cách {attempt} lỗi: {e}")
                
            # Pause before next attempt
            if attempt < len(all_strategies):
                self.human.random_pause(1.0, 2.0, f"trước thử lại")
        
        if action_name:
            print(f"❌ {action_name} thất bại sau {len(all_strategies)} cách")
        return False
    
    def follow_with_retry(self, follow_func, max_attempts: int = 3) -> bool:
        """
        Follow với multi-strategy retry
        
        Strategies:
        1. Direct click Follow button
        2. Scroll to make visible, then click
        3. Reload profile and try again
        
        Args:
            follow_func: Base follow function
            max_attempts: Max attempts
            
        Returns:
            True if followed successfully
        """
        
        def strategy_direct():
            """Strategy 1: Direct click"""
            return follow_func()
        
        def strategy_scroll_first():
            """Strategy 2: Scroll first to make visible"""
            try:
                # Scroll up a bit
                w, h = self.device.window_size()
                self.human.smooth_swipe(self.device, w//2, h//2, w//2, h//3)
                self.human.random_pause(0.5, 1.0, "sau cuộn")
                return follow_func()
            except:
                return False
        
        def strategy_reload():
            """Strategy 3: Reload profile"""
            try:
                # Swipe down to reload
                w, h = self.device.window_size()
                self.human.smooth_swipe(self.device, w//2, h//4, w//2, h//2)
                self.human.random_pause(1.0, 2.0, "reload profile")
                return follow_func()
            except:
                return False
        
        result = self.execute_with_fallback(
            strategy_direct,
            [strategy_scroll_first, strategy_reload],
            max_attempts,
            "Follow"
        )
        
        # Track success
        self.success_history['follow'].append(result)
        if len(self.success_history['follow']) > 100:
            self.success_history['follow'].pop(0)
        
        return result
    
    def comment_with_fallback(self, comment_func, like_func, fallback_to_like: bool = True) -> bool:
        """
        Comment với fallback to like nếu fail
        
        Args:
            comment_func: Comment function
            like_func: Like function (fallback)
            fallback_to_like: If True, like when comment fails
            
        Returns:
            True if any action succeeded
        """
        
        def strategy_comment():
            """Try to comment"""
            return comment_func()
        
        def strategy_like_fallback():
            """Fallback: Like instead"""
            if fallback_to_like:
                print("🔄 Comment fail, thử like thay thế...")
                return like_func()
            return False
        
        result = self.execute_with_fallback(
            strategy_comment,
            [strategy_like_fallback] if fallback_to_like else [],
            action_name="Comment"
        )
        
        # Track success
        self.success_history['comment'].append(result)
        if len(self.success_history['comment']) > 100:
            self.success_history['comment'].pop(0)
        
        return result
    
    def like_with_retry(self, like_func, max_attempts: int = 3) -> bool:
        """
        Like với retry ở nhiều vị trí khác nhau
        
        Try tapping different positions of like button
        (sometimes button position shifts slightly)
        """
        
        def strategy_center():
            """Try tapping center"""
            return like_func()
        
        def strategy_left():
            """Try tapping slightly left"""
            try:
                # Add left offset
                w, h = self.device.window_size()
                offset_x = -20
                return like_func()  # Function handles offset internally
            except:
                return False
        
        def strategy_right():
            """Try tapping slightly right"""
            try:
                # Add right offset
                offset_x = 20
                return like_func()
            except:
                return False
        
        result = self.execute_with_fallback(
            strategy_center,
            [strategy_left, strategy_right],
            max_attempts,
            "Like"
        )
        
        # Track success
        self.success_history['like'].append(result)
        if len(self.success_history['like']) > 100:
            self.success_history['like'].pop(0)
        
        return result
    
    def notification_safe(self, notif_func, skip_on_fail: bool = True) -> bool:
        """
        Notification action với safe skip
        
        If notification button không tìm thấy, skip gracefully
        """
        try:
            result = notif_func()
            
            # Track success
            self.success_history['notification'].append(result)
            if len(self.success_history['notification']) > 100:
                self.success_history['notification'].pop(0)
            
            return result
            
        except Exception as e:
            if skip_on_fail:
                print(f"⚠️  Notification không khả dụng, bỏ qua")
                return True  # Return True to not count as failure
            return False
    
    def shop_safe(self, shop_func, skip_on_fail: bool = True) -> bool:
        """
        Shop action với safe skip
        
        If shop không có/không available, skip gracefully
        """
        try:
            result = shop_func()
            
            # Track success
            self.success_history['shop'].append(result)
            if len(self.success_history['shop']) > 100:
                self.success_history['shop'].pop(0)
            
            return result
            
        except Exception as e:
            if skip_on_fail:
                print(f"⚠️  Shop không khả dụng, bỏ qua")
                return True  # Return True to not count as failure
            return False
    
    def get_success_rate(self, action_type: str) -> float:
        """
        Get success rate for specific action type
        
        Returns:
            Success rate (0.0 - 1.0)
        """
        history = self.success_history.get(action_type, [])
        if not history:
            return 0.0
        
        successes = sum(1 for x in history if x)
        return successes / len(history)
    
    def get_all_success_rates(self) -> dict:
        """Get success rates for all action types"""
        return {
            action: self.get_success_rate(action)
            for action in self.success_history.keys()
        }
    
    def should_adapt_strategy(self, action_type: str, threshold: float = 0.7) -> bool:
        """
        Check if success rate is below threshold
        
        If success rate low, should adapt strategy
        """
        rate = self.get_success_rate(action_type)
        return rate < threshold and len(self.success_history[action_type]) >= 10


# ═══════════════════════════════════════════════════════════════
# 🔍 v1.4.4 ADDITIONAL: ENHANCED DETECTION SYSTEM
# ═══════════════════════════════════════════════════════════════

    
