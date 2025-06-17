import google.generativeai as genai
import os
import json
import logging

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- PROMPT FOR SCHEMA.ORG JSON ---
SCHEMA_ORG_LLM_PROMPT_TEMPLATE = """
You are an expert recipe JSON generator.
I will provide you with **raw text extracted directly from a recipe**.
Your task is to accurately parse ONLY this provided text and generate a valid JSON-LD object for a Recipe following the Schema.org vocabulary.

**CRUCIAL GUIDELINES - STRICTLY ADHERE TO THESE:**
1.  **DO NOT HALLUCINATE OR INVENT ANY INFORMATION.** All recipe details (ingredients, instructions, times, yield, etc.) MUST come SOLELY from the provided "Recipe Text to Parse".
2.  If a piece of information (e.g., specific cookTime, recipeCategory, recipeCuisine, or an ingredient amount) is NOT clearly present in the provided text, either **omit that field entirely** from the JSON or provide a very generic placeholder like "Unknown" (prefer omission for missing details unless a field is mandatory for Schema.org and can be generically filled, like "1 serving" for servingSize if not found).
3.  The JSON MUST start with `{{\"@context\": \"https://schema.org/\", \"@type\": \"Recipe\", ...}}`.
4.  All recipe ingredients MUST be combined into a single `recipeIngredient` array, where each element is a string... Include measurements and descriptions exactly as found in the text.
5.  Each instruction step MUST be a separate object in the `recipeInstructions` array, with `@type: "HowToStep"` and `text: "Instruction text."`. **Carefully break down the recipe into distinct, logical, and concise steps, even if the original text combines multiple actions into one paragraph. Each step should represent one clear instruction or a small group of highly related actions.**
6.  Estimate `prepTime`, `cookTime`, and `totalTime` in ISO 8601 duration format (e.g., "PT30M" for 30 minutes, "PT1H15M" for 1 hour 15 minutes, "PT2H" for 2 hours, "PT7H" for 7 hours). Base estimations strictly on time indications within the text. If no explicit times, try to estimate roughly or omit.
7.  `recipeYield` should be a descriptive string like "4 servings" or "Makes 1.5 litres", based *only* on the provided text.
8.  If 'author' is not specified in the text, use "Recipe Book".
9.  For 'image', use a descriptive text string like "close up view of [dish name] on a [color] platter", inferring [dish name] from the recipe title.
10. If there's a 'note' or general tips/context in the original text, include it in the 'note' field.
11. If nutrition information is missing, provide a generic `servingSize` like "1 serving".

**--- START OF RECIPE TEXT ---**
{recipe_text}
**--- END OF RECIPE TEXT ---**

**Output ONLY the JSON object. Do NOT include any other text, explanations, or markdown outside the JSON block.**
"""

# --- PROMPT FOR CREATE_RECIPE INTERMEDIATE JSON ---
CREATE_RECIPE_LLM_PROMPT_TEMPLATE = """
You are an expert recipe JSON generator.
I will provide you with **raw text extracted directly from a recipe**.
Your task is to accurately parse ONLY this provided text and generate a VALID JSON object for the recipe data, conforming to a specific intermediate schema. This schema aims to extract all semantic details clearly for later processing into a more complex system.

**CRUCIAL GUIDELINES - STRICTLY ADHERE TO THESE:**
1.  **DO NOT HALLUCINATE OR INVENT ANY INFORMATION.** All recipe details MUST come SOLELY from the provided "Recipe Text to Parse".
2.  If a piece of information is NOT clearly present in the provided text, **OMIT that specific field** from the JSON, UNLESS explicitly told to set a default value below. Do not use 'string', 'null', or magic numbers (-2147483648) as placeholders.
3.  The top-level JSON object should contain: `name`, `description`, `keywords`, `steps`, `working_time`, `waiting_time`, `source_url`, `nutrition`, `servings`, `servings_text`.
4.  For `keywords`: Provide an array of objects `[{{ "name": "string", "description": "string" }}]`. Infer common keywords (e.g., "dessert", "vegetarian") and a very brief description for them based on the text. If no keywords, use an empty array `[]`.
5.  For `steps`: Provide an array of objects `[{{ "name": "string", "instruction": "string", "ingredients": [...], "time": int, "order": int, "show_as_header": bool, "show_ingredients_table": bool }}]`.
    * **Break down the recipe into distinct, logical, and concise steps.**
    * **If the original text uses "Step N" or similar numbered/bulleted step indicators, use those as guides for splitting steps.** Otherwise, split by clear paragraph breaks or distinct instructional units.
    * **CRITICAL:** Every step object MUST have a `name` (even if generic like "Step") and `instruction`. If a logical step cannot be fully parsed, omit the entire step object rather than leaving it empty.
    * `name`: A concise title for the step (e.g., "Prepare Dough", "Bake Tart", or "Step 1").
    * `instruction`: The detailed text for the step.
    * `ingredients`: This array will contain **ALL ingredients for the entire recipe**. The full detailed ingredient list should be placed here, in the **first step (order: 0)**. For all subsequent steps (order > 0), the `ingredients` array should be empty `[]`.
        * Each ingredient object should be `[{{ "food": {{ "name": "string", "plural_name": "string" }}, "unit": {{ "name": "string", "plural_name": "string" }}, "amount": float, "note": "string" }}]`.
        * `food.name`: The singular name of the food (e.g., "sugar", "egg", "flour").
        * `food.plural_name`: The plural name if clear (e.g., "eggs"), otherwise default to `food.name` + "s" (e.g., "sugars", "flours").
        * `unit.name`: The singular name of the unit (e.g., "cup", "teaspoon", "gram"). If no unit is mentioned, set to "item".
        * `unit.plural_name`: The plural name if clear. If no unit is mentioned, set to "items".
        * `amount`: The numerical amount (e.g., `1.0`, `0.5`, `2.0`). If no amount is mentioned, set to `0.0`.
        * `note`: Any additional notes (e.g., "finely chopped", "cold", "optional"), otherwise omit.
        * **Omit** `order`, `is_header`, `no_amount`, `original_text`, `always_use_plural_unit`, `always_use_plural_food`, `ignore_shopping`, `supermarket_category`, and other complex nested fields from the `ingredients` objects; these will be handled by post-processing.
    * `time`: The explicit time for this step in minutes (e.g., "5", "30"). If a range (e.g., "5-7 minutes"), use the upper bound or an average, as an integer. If no time is explicitly mentioned in the text for a step, set this field to `0` (zero).
    * `order`: The numerical order of the step, starting from 0.
    * `show_as_header`: Always `true` if the step has a `name`.
    * `show_ingredients_table`: `true` if `ingredients` array for this step is not empty, `false` otherwise.
    * **Omit** `file` and `step_recipe` for now; these will be handled by post-processing.
6.  `working_time`: Extract this as an integer (minutes) if explicitly mentioned. **If not mentioned, set this field to `0` (zero).**
7.  `waiting_time`: Extract this as an integer (minutes) if explicitly mentioned. **If not mentioned, set this field to `0` (zero).**
8.  `source_url`: If a URL is present, extract it. Otherwise, omit.
9.  `nutrition`: If explicit fields (`carbohydrates`, `fats`, `proteins`, `calories`, `source`) are found, provide them as strings. Otherwise, omit the entire `nutrition` object.
10. `servings`: Extract the number of servings as an integer.
11. `servings_text`: Extract the descriptive serving text (e.g., "4 servings", "Makes 1.5 litres"). **Note: This field needs a character limit check (e.g., if > 32 chars, set to 'empty') in a separate Python post-processing script, as the LLM cannot reliably perform this precise validation during generation.**
12. **Omit** `main_ingredients_section` (this field is no longer needed as all ingredients go into the first step directly), `properties`, `file_path`, `private`, `shared` from the top level; these will be handled by post-processing.

**--- START OF RECIPE TEXT ---**
{recipe_text}
**--- END OF RECIPE TEXT ---**

**Output ONLY the JSON object. Do NOT include any other text, explanations, or markdown outside the JSON block.**
"""

def get_schema_org_json(raw_text):
    """
    Sends raw recipe text to a Gemini LLM and returns Schema.org Recipe JSON.
    """
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY is not set in the .env file.")
        return None

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = SCHEMA_ORG_LLM_PROMPT_TEMPLATE.format(recipe_text=raw_text)
        response = model.generate_content(prompt)

        if response and response.candidates:
            json_str = response.text.strip()
            if json_str.startswith("```json") and json_str.endswith("```"):
                json_str = json_str[7:-3].strip()

            try:
                recipe_json = json.loads(json_str)
                return recipe_json
            except json.JSONDecodeError as e:
                logger.error(f"LLM returned invalid JSON: {e}\nRaw LLM output: {json_str}")
                return None
        else:
            logger.warning(f"LLM response contained no text candidates for processing.")
            return None

    except Exception as e:
        logger.exception(f"Error calling LLM API for Schema.org: {e}")
        return None

def get_create_recipe_json_intermediate(raw_text):
    """
    Sends raw recipe text to a Gemini LLM and returns the intermediate Custom JSON.
    """
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY is not set in the .env file.")
        return None

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = CREATE_RECIPE_LLM_PROMPT_TEMPLATE.format(recipe_text=raw_text)
        response = model.generate_content(prompt)

        if response and response.candidates:
            json_str = response.text.strip()
            if json_str.startswith("```json") and json_str.endswith("```"):
                json_str = json_str[7:-3].strip()

            try:
                recipe_json = json.loads(json_str)
                return recipe_json
            except json.JSONDecodeError as e:
                logger.error(f"LLM returned invalid JSON: {e}\nRaw LLM output: {json_str}")
                return None
        else:
            logger.warning(f"LLM response contained no text candidates for processing.")
            return None

    except Exception as e:
        logger.exception(f"Error calling LLM API for createRecipe: {e}")
        return None
