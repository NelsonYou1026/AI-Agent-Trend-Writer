import datetime
from typing import Dict

class ContentFormatter:
    """
    Formats the raw output from AI agents into clean, structured markdown files.
    """

    @staticmethod
    def _load_template(path: str) -> str:
        """Loads a template file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""

    @staticmethod
    def format_video_script(topic: str, script_content: str, source: str) -> str:
        """
        Formats the generated video script using a template.

        Args:
            topic (str): The content topic.
            script_content (str): The raw script from the agent.
            source (str): The source of the trend.

        Returns:
            str: A formatted markdown string for the video script.
        """
        # 直接使用原始內容，不依賴特定格式
        if not script_content or script_content.strip() == "":
            script_content = "無法生成影片腳本內容"
        
        # 加上標題和元資料
        formatted_content = f"# {topic} - 影片腳本\n\n{script_content.strip()}\n\n"
        
        metadata = (
            f"---\n"
            f"*主題: {topic}*\n"
            f"*來源: {source}*\n"
            f"*生成時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        )
        return formatted_content + metadata

    @staticmethod
    def format_social_media(topic: str, social_content: str, source: str) -> str:
        """
        Formats the generated social media content using a template.

        Args:
            topic (str): The content topic.
            social_content (str): The raw social media content from the agent.
            source (str): The source of the trend.

        Returns:
            str: A formatted markdown string for social media posts.
        """
        # 直接使用原始內容，不依賴特定格式
        if not social_content or social_content.strip() == "":
            social_content = "無法生成社群媒體內容"
            
        # 加上標題和元資料
        formatted_content = f"# {topic} - 社群媒體文案\n\n{social_content.strip()}\n\n"

        metadata = (
            f"---\n"
            f"*主題: {topic}*\n"
            f"*來源: {source}*\n"
            f"*生成時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        )
        return formatted_content + metadata

if __name__ == '__main__':
    # Example Usage
    raw_script = """
    **Hook (0-10s):**
    Did you know the sky isn't really blue?
    **Main Content (10-50s):**
    It's all about light scattering.
    **Call-to-Action (50-60s):**
    Subscribe for more science facts!
    """
    raw_social = """
    ## Instagram/Facebook
    [Image of a beautiful blue sky] Wow! Science is cool. #science #sky #blue
    ## Twitter/X
    Thread: Why is the sky blue? 🧵 1/3
    ## LinkedIn
    The physics of Rayleigh scattering has implications for...
    """
    
    formatted_script = ContentFormatter.format_video_script("Why the Sky is Blue", raw_script, "Curiosity")
    formatted_social = ContentFormatter.format_social_media("Why the Sky is Blue", raw_social, "Curiosity")

    print("--- Formatted Video Script ---")
    print(formatted_script)
    print("\n--- Formatted Social Media ---")
    print(formatted_social)
