#!/usr/bin/env python3
"""
開發者反饋收集工具

此腳本用於收集開發者對新檔案結構的反饋，
並生成反饋報告。

Usage:
    python scripts/collect_feedback.py
    python scripts/collect_feedback.py --survey
    python scripts/collect_feedback.py --report
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import webbrowser


class FeedbackCollector:
    """反饋收集器"""
    
    def __init__(self):
        self.feedback_file = Path("feedback_data.json")
        self.feedback_data = self.load_existing_feedback()
    
    def load_existing_feedback(self) -> Dict[str, Any]:
        """載入現有反饋數據"""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 載入反饋數據失敗: {e}")
        
        return {
            'surveys': [],
            'issues': [],
            'suggestions': [],
            'statistics': {
                'total_feedback': 0,
                'average_satisfaction': 0.0,
                'common_issues': []
            }
        }
    
    def save_feedback(self):
        """保存反饋數據"""
        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_data, f, indent=2, ensure_ascii=False)
            print(f"✅ 反饋數據已保存到: {self.feedback_file}")
        except Exception as e:
            print(f"❌ 保存反饋數據失敗: {e}")
    
    def conduct_survey(self):
        """進行反饋問卷調查"""
        print("📋 檔案結構使用體驗調查")
        print("=" * 40)
        print("感謝您參與我們的調查！您的反饋對改進系統非常重要。")
        print()
        
        survey_data = {
            'timestamp': datetime.now().isoformat(),
            'responses': {}
        }
        
        # 基本資訊
        print("📊 基本資訊")
        print("-" * 20)
        
        experience_levels = {
            '1': '新手 (< 1年經驗)',
            '2': '中級 (1-3年經驗)',
            '3': '高級 (> 3年經驗)'
        }
        
        print("您的開發經驗:")
        for key, value in experience_levels.items():
            print(f"  {key}. {value}")
        
        while True:
            experience = input("請選擇 (1-3): ").strip()
            if experience in experience_levels:
                survey_data['responses']['experience'] = experience_levels[experience]
                break
            print("❌ 請輸入有效選項 (1-3)")
        
        usage_time_options = {
            '1': '少於 1 週',
            '2': '1-2 週',
            '3': '2-4 週',
            '4': '超過 1 個月'
        }
        
        print("\n使用新結構的時間:")
        for key, value in usage_time_options.items():
            print(f"  {key}. {value}")
        
        while True:
            usage_time = input("請選擇 (1-4): ").strip()
            if usage_time in usage_time_options:
                survey_data['responses']['usage_time'] = usage_time_options[usage_time]
                break
            print("❌ 請輸入有效選項 (1-4)")
        
        # 使用體驗評分
        print("\n⭐ 使用體驗評分 (1-5分，5分最好)")
        print("-" * 30)
        
        rating_questions = [
            ('ease_of_use', '新模組結構的易用性'),
            ('migration_guide', '遷移指南的清晰度'),
            ('documentation', '文檔的完整性'),
            ('overall_satisfaction', '整體滿意度')
        ]
        
        for key, question in rating_questions:
            while True:
                try:
                    rating = int(input(f"{question} (1-5): ").strip())
                    if 1 <= rating <= 5:
                        survey_data['responses'][key] = rating
                        break
                    else:
                        print("❌ 請輸入 1-5 之間的數字")
                except ValueError:
                    print("❌ 請輸入有效的數字")
        
        # 開放式問題
        print("\n💭 開放式問題")
        print("-" * 20)
        
        open_questions = [
            ('biggest_difficulty', '您在遷移過程中遇到的最大困難是什麼？'),
            ('best_module', '哪個模組的使用體驗最好？為什麼？'),
            ('improvement_needed', '哪個模組需要改進？具體建議？'),
            ('additional_docs', '您希望看到哪些額外的文檔或工具？'),
            ('other_suggestions', '其他建議或想法：')
        ]
        
        for key, question in open_questions:
            response = input(f"{question}\n> ").strip()
            survey_data['responses'][key] = response if response else "無回應"
        
        # 保存調查結果
        self.feedback_data['surveys'].append(survey_data)
        self.update_statistics()
        self.save_feedback()
        
        print("\n✅ 感謝您的反饋！您的意見對我們非常寶貴。")
        print("📊 您可以運行 'python scripts/collect_feedback.py --report' 查看統計報告")
    
    def update_statistics(self):
        """更新統計資訊"""
        surveys = self.feedback_data['surveys']
        if not surveys:
            return
        
        # 計算平均滿意度
        satisfaction_scores = []
        for survey in surveys:
            responses = survey.get('responses', {})
            if 'overall_satisfaction' in responses:
                satisfaction_scores.append(responses['overall_satisfaction'])
        
        if satisfaction_scores:
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
            self.feedback_data['statistics']['average_satisfaction'] = round(avg_satisfaction, 2)
        
        # 更新總反饋數
        total_feedback = (len(self.feedback_data['surveys']) + 
                         len(self.feedback_data['issues']) + 
                         len(self.feedback_data['suggestions']))
        self.feedback_data['statistics']['total_feedback'] = total_feedback
        
        # 分析常見問題
        difficulties = []
        for survey in surveys:
            responses = survey.get('responses', {})
            difficulty = responses.get('biggest_difficulty', '')
            if difficulty and difficulty != "無回應":
                difficulties.append(difficulty)
        
        # 簡單的關鍵詞統計（實際應用中可以使用更複雜的 NLP）
        common_keywords = {}
        for difficulty in difficulties:
            words = difficulty.lower().split()
            for word in words:
                if len(word) > 3:  # 忽略短詞
                    common_keywords[word] = common_keywords.get(word, 0) + 1
        
        # 取前5個最常見的關鍵詞
        sorted_keywords = sorted(common_keywords.items(), key=lambda x: x[1], reverse=True)
        self.feedback_data['statistics']['common_issues'] = sorted_keywords[:5]
    
    def generate_report(self) -> str:
        """生成反饋報告"""
        stats = self.feedback_data['statistics']
        surveys = self.feedback_data['surveys']
        
        report = []
        report.append("📊 開發者反饋統計報告")
        report.append("=" * 50)
        report.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 基本統計
        report.append("📈 基本統計")
        report.append("-" * 20)
        report.append(f"總反饋數: {stats['total_feedback']}")
        report.append(f"問卷調查數: {len(surveys)}")
        report.append(f"平均滿意度: {stats['average_satisfaction']}/5.0")
        report.append("")
        
        if surveys:
            # 體驗評分統計
            report.append("⭐ 體驗評分統計")
            report.append("-" * 20)
            
            rating_categories = [
                ('ease_of_use', '易用性'),
                ('migration_guide', '遷移指南'),
                ('documentation', '文檔完整性'),
                ('overall_satisfaction', '整體滿意度')
            ]
            
            for key, name in rating_categories:
                scores = []
                for survey in surveys:
                    responses = survey.get('responses', {})
                    if key in responses:
                        scores.append(responses[key])
                
                if scores:
                    avg_score = sum(scores) / len(scores)
                    report.append(f"{name}: {avg_score:.2f}/5.0 ({len(scores)} 個評分)")
            
            report.append("")
            
            # 使用者背景分析
            report.append("👥 使用者背景分析")
            report.append("-" * 20)
            
            experience_count = {}
            usage_time_count = {}
            
            for survey in surveys:
                responses = survey.get('responses', {})
                
                experience = responses.get('experience', '未知')
                experience_count[experience] = experience_count.get(experience, 0) + 1
                
                usage_time = responses.get('usage_time', '未知')
                usage_time_count[usage_time] = usage_time_count.get(usage_time, 0) + 1
            
            report.append("開發經驗分佈:")
            for exp, count in experience_count.items():
                report.append(f"  - {exp}: {count} 人")
            
            report.append("\n使用時間分佈:")
            for time, count in usage_time_count.items():
                report.append(f"  - {time}: {count} 人")
            
            report.append("")
            
            # 常見問題
            if stats['common_issues']:
                report.append("🔥 常見問題關鍵詞")
                report.append("-" * 20)
                for keyword, count in stats['common_issues']:
                    report.append(f"  - {keyword}: {count} 次提及")
                report.append("")
            
            # 最新反饋摘要
            report.append("💬 最新反饋摘要")
            report.append("-" * 20)
            
            recent_surveys = sorted(surveys, key=lambda x: x['timestamp'], reverse=True)[:3]
            for i, survey in enumerate(recent_surveys, 1):
                responses = survey['responses']
                timestamp = survey['timestamp'][:10]  # 只顯示日期
                
                report.append(f"{i}. {timestamp}")
                report.append(f"   滿意度: {responses.get('overall_satisfaction', 'N/A')}/5")
                
                difficulty = responses.get('biggest_difficulty', '')
                if difficulty and difficulty != "無回應":
                    report.append(f"   主要困難: {difficulty[:50]}...")
                
                suggestion = responses.get('other_suggestions', '')
                if suggestion and suggestion != "無回應":
                    report.append(f"   建議: {suggestion[:50]}...")
                
                report.append("")
        
        # 行動建議
        report.append("🔧 建議行動")
        report.append("-" * 20)
        
        if stats['average_satisfaction'] < 3.0:
            report.append("⚠️ 滿意度偏低，需要緊急改進")
        elif stats['average_satisfaction'] < 4.0:
            report.append("📈 滿意度中等，有改進空間")
        else:
            report.append("✅ 滿意度良好，繼續保持")
        
        if stats['common_issues']:
            report.append("🎯 重點關注以下問題:")
            for keyword, count in stats['common_issues'][:3]:
                report.append(f"  - {keyword} 相關問題")
        
        report.append("\n📋 下一步行動:")
        report.append("  1. 分析具體反饋內容")
        report.append("  2. 優先處理高頻問題")
        report.append("  3. 更新文檔和指南")
        report.append("  4. 持續收集反饋")
        
        return "\n".join(report)
    
    def open_github_discussion(self):
        """打開 GitHub Discussion 頁面"""
        url = "https://github.com/Cookieeeeeeeeeeeeeee/ai_trading/discussions"
        try:
            webbrowser.open(url)
            print(f"🌐 已在瀏覽器中打開 GitHub Discussion: {url}")
        except Exception as e:
            print(f"❌ 無法打開瀏覽器: {e}")
            print(f"請手動訪問: {url}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='開發者反饋收集工具')
    parser.add_argument('--survey', action='store_true', help='進行反饋問卷調查')
    parser.add_argument('--report', action='store_true', help='生成反饋報告')
    parser.add_argument('--github', action='store_true', help='打開 GitHub Discussion')
    
    args = parser.parse_args()
    
    collector = FeedbackCollector()
    
    if args.survey:
        collector.conduct_survey()
    elif args.report:
        report = collector.generate_report()
        print(report)
        
        # 保存報告到檔案
        report_file = f"feedback_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 報告已保存到: {report_file}")
    elif args.github:
        collector.open_github_discussion()
    else:
        # 預設顯示選項
        print("📋 開發者反饋收集工具")
        print("=" * 30)
        print("請選擇操作:")
        print("  1. 進行反饋問卷調查 (--survey)")
        print("  2. 生成反饋報告 (--report)")
        print("  3. 打開 GitHub Discussion (--github)")
        print()
        print("使用範例:")
        print("  python scripts/collect_feedback.py --survey")
        print("  python scripts/collect_feedback.py --report")


if __name__ == '__main__':
    main()
