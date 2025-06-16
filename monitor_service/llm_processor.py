import google.generativeai as genai
import os
import json
import logging

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# The precise prompt to get the Schema.org JSON
LLM_PROMPT_TEMPLATE = """
You are an expert recipe JSON generator.
I will provide you with raw text extracted from a recipe. Your task is to accurately parse this text and generate a valid JSON-LD object for a Recipe following the Schema.org vocabulary.

**Crucial Instructions:**
1.  The JSON MUST start with `{"@context": "https://schema.org/", "@type": "Recipe", ...}`.
2.  All recipe ingredients MUST be combined into a single `recipeIngredient` array, where each element is a string (e.g., "1 cup sugar", "2 large eggs"). Include measurements and descriptions.
3.  Each instruction step MUST be a separate object in the `recipeInstructions` array, with `@type: "HowToStep"` and `text: "Instruction text."`.
4.  If not explicitly stated, estimate `prepTime`, `cookTime`, and `totalTime` in ISO 8601 duration format (e.g., "PT30M" for 30 minutes, "PT1H15M" for 1 hour 15 minutes, "PT2H" for 2 hours, "PT7H" for 7 hours).
5.  `recipeYield` should be a descriptive string like "4 servings" or "Makes about 1.5 litres".
6.  If 'author' is not specified, use "Recipe Book".
7.  Include `recipeCategory` and `recipeCuisine` if inferable.
8.  Include a `description` for the recipe.
9.  For 'image', use a descriptive text string like "close up view of [dish name] on a [color] platter".
10. If there's a 'note' or general tips/context in the original text, include it in the 'note' field.
11. If nutrition information is missing, provide a generic `servingSize` like "1 serving".

**Recipe Text to Parse:**
{recipe_text}
**Output ONLY the JSON object. Do NOT include any other text, explanations, or markdown outside the JSON block.**
"""

def get_recipe_json(raw_text):
    """
    Sends raw recipe text to a Gemini LLM and returns Schema.org Recipe JSON.
    """
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY is not set in the .env file.")
        return None

    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = LLM_PROMPT_TEMPLATE.format(recipe_text=raw_text)
        response = model.generate_content(prompt)

        # Access the text from the candidate, handling potential errors
        if response and response.candidates:
            json_str = response.candidates[0].text.strip()
            # The LLM might sometimes wrap the JSON in markdown code blocks.
            # Attempt to strip it if present.
            if json_str.startswith("```json") and json_str.endswith("```"):
                json_str = json_str[7:-3].strip() # Remove ```json and ```

            try:
                # Validate JSON before returning
                recipe_json = json.loads(json_str)
                return recipe_json
            except json.JSONDecodeError as e:
                logger.error(f"LLM returned invalid JSON: {e}\nRaw LLM output: {json_str}")
                return None
        else:
            logger.warning(f"LLM response contained no text candidates for processing.")
            return None

    except Exception as e:
        logger.exception(f"Error calling LLM API: {e}")
        return None

