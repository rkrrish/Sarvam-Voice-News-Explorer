import json
import re
import logging
from typing import Dict, Any, List, Optional
from sarvamai import SarvamAI
from app.config import SARVAM_API_KEY, SARVAM_LLM_MODEL

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "en-IN": "English (Indian)",
    "hi-IN": "Hindi (हिंदी)",
    "bn-IN": "Bengali (বাংলা)",
    "kn-IN": "Kannada (ಕನ್ನಡ)",
    "ml-IN": "Malayalam (മലയാളം)",
    "mr-IN": "Marathi (मराठी)",
    "od-IN": "Odia (ଓଡ଼ିଆ)",
    "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
    "ta-IN": "Tamil (தமிழ்)",
    "te-IN": "Telugu (తెలుగు)",
    "gu-IN": "Gujarati (ગુજરાતી)",
}

class LLMService:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or SARVAM_API_KEY
        if not key:
            raise ValueError("SARVAM_API_KEY is not set.")
        self.client = SarvamAI(api_subscription_key=key)

    def analyze_query_and_extract_search(
        self,
        prompt: str,
        input_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send the user's voice input prompt to the Sarvam LLM to analyze what
        the user wants to know and create optimized keywords/sentences for NewsAPI.
        """
        system_prompt = """You are an expert news search query optimizer.
Your task is to analyze the user's voice input prompt to determine what information they want to know.
Then, create a concise, highly relevant English search query or sentence and specific search keywords to be sent to NewsAPI.

CRITICAL INSTRUCTIONS:
1. Identify the core intent of the user.
2. Even if the user prompt is in an Indian language (such as Hindi, Tamil, Bengali, etc.), formulate the 'search_query' and 'keywords' in ENGLISH so they can be effectively searched on NewsAPI.
3. Keep the 'search_query' concise (2-5 key words/entities) without conversational noise (e.g. without 'tell me', 'what happened', 'was there').
4. Return ONLY a valid JSON object with the following schema:
{
  "user_intent": "Explanation of what the user is looking for",
  "search_query": "targeted English search sentence/phrase for NewsAPI",
  "keywords": ["key entity 1", "key entity 2", "topic"]
}
Do NOT output markdown backticks or any additional conversational text. Return pure JSON.
"""

        try:
            response = self.client.chat.completions(
                model=SARVAM_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User Voice Input: {prompt.strip()}"}
                ],
                temperature=0.1
            )
            raw_text = response.choices[0].message.content or "{}"
            parsed = self._parse_json_object(raw_text)

            search_query = parsed.get("search_query", "").strip() or prompt.strip()
            keywords = parsed.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = [str(keywords)]
            user_intent = parsed.get("user_intent", f"Search for information about: {prompt}")

            return {
                "success": True,
                "user_intent": user_intent,
                "search_query": search_query,
                "keywords": keywords,
                "model": SARVAM_LLM_MODEL,
                "raw_response": raw_text
            }
        except Exception as e:
            logger.error(f"Error in LLM query analysis: {e}", exc_info=True)
            return {
                "success": False,
                "user_intent": f"User asked: {prompt}",
                "search_query": prompt.strip(),
                "keywords": [prompt.strip()],
                "model": SARVAM_LLM_MODEL,
                "error": str(e)
            }

    def _parse_json_object(self, text: str) -> Dict[str, Any]:
        """Helper to extract JSON object from LLM response."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return {}

    def generate_answer(
        self,
        query: str,
        articles: List[Dict[str, Any]],
        language_code: str = "en-IN"
    ) -> Dict[str, Any]:
        """
        Process the retrieved news articles to determine if the query was answered,
        cite provenance, and generate the response in the user's input language.
        """
        target_language_name = LANGUAGE_NAMES.get(language_code, "English")

        # Format articles context
        articles_context_lines = []
        for a in articles:
            articles_context_lines.append(
                f"[Article {a['index']} - {a['id']}]\n"
                f"Title: {a['title']}\n"
                f"Source: {a['source']}\n"
                f"Date: {a['published_at']}\n"
                f"Summary: {a['description']}\n"
                f"Content: {a['content'][:350]}\n"
            )
        articles_context = "\n".join(articles_context_lines) if articles_context_lines else "No articles retrieved."

        system_prompt = f"""You are a helpful, factual multilingual AI news research analyst.
Your task is to analyze the provided news articles and answer the user's query with rigorous accuracy and provenance tracking.

CRITICAL INSTRUCTIONS:
1. Grounding: Answer ONLY based on the provided news articles. If the articles do not contain enough facts to answer the question, state that clearly.
2. Multilingual Output: You MUST write your final response ('answer' and 'audio_script') in {target_language_name} ({language_code}), matching the user's language.
3. Provenance & Citations: Explicitly mention which Article indices (e.g., [Article 1], [Article 2]) support each statement.
4. Audio Script: Provide a clean 'audio_script' in the target language suitable for Text-to-Speech (omit markdown symbols) and mention the date of the cited article on which the news was released on.
5. Output Format: You MUST return ONLY a valid JSON object with the following schema:
{{
  "answered": true, // boolean: true if the question was answered, false if not enough info
  "answer": "Detailed answer in {target_language_name} with citations [Article 1]",
  "audio_script": "Natural spoken sentence in {target_language_name} without citations",
  "cited_article_indices": [1, 2], // array of integers
  "reasoning": "Short explanation of findings in English"
}}
Do NOT output any markdown backticks outside the JSON or conversational preamble. Return pure JSON.
"""

        user_content = f"""User Question: {query}
Target Response Language: {target_language_name} ({language_code})

Retrieved News Articles Context:
{articles_context}
"""

        prompt_payload = {
            "model": SARVAM_LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2
        }

        try:
            response = self.client.chat.completions(**prompt_payload)
            raw_content = response.choices[0].message.content or "{}"
            parsed = self._parse_json_response(raw_content, language_code)

            # Map cited article indices back to article objects
            cited_articles = []
            for idx in parsed.get("cited_article_indices", []):
                matching = next((a for a in articles if a["index"] == idx), None)
                if matching:
                    cited_articles.append({
                        "id": matching["id"],
                        "index": matching["index"],
                        "title": matching["title"],
                        "source": matching["source"],
                        "url": matching["url"]
                    })

            return {
                "success": True,
                "answered": parsed.get("answered", False),
                "answer": parsed.get("answer", raw_content),
                "audio_script": parsed.get("audio_script", parsed.get("answer", raw_content)),
                "cited_article_indices": parsed.get("cited_article_indices", []),
                "cited_articles": cited_articles,
                "reasoning": parsed.get("reasoning", ""),
                "language_code": language_code,
                "prompt_payload": {
                    "system_prompt": system_prompt,
                    "user_content": user_content,
                    "model": SARVAM_LLM_MODEL
                },
                "raw_response": raw_content
            }

        except Exception as e:
            logger.error(f"LLM Error: {e}", exc_info=True)
            return {
                "success": False,
                "answered": False,
                "answer": f"Error generating answer: {str(e)}",
                "audio_script": f"Sorry, an error occurred while processing the news.",
                "cited_article_indices": [],
                "cited_articles": [],
                "reasoning": str(e),
                "language_code": language_code,
                "prompt_payload": {},
                "raw_response": ""
            }

    def _parse_json_response(self, text: str, language_code: str) -> Dict[str, Any]:
        """Safely extract and parse JSON from model output."""
        cleaned = text.strip()
        # Remove markdown code blocks if wrapped
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception:
            # Fallback regex extraction of JSON object
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass

            return {
                "answered": True if len(text) > 40 else False,
                "answer": text,
                "audio_script": re.sub(r"\[Article \d+\]", "", text).strip(),
                "cited_article_indices": [1] if text else [],
                "reasoning": "Parsed as fallback text response."
            }

llm_service = LLMService()
