from google.genai import types
from google.adk.runners import Runner
from google.adk.agents import SequentialAgent , ParallelAgent
import json , shutil , re , subprocess
from pathlib import Path





generate_content_config = types.GenerateContentConfig(
        # 🔒 Enforce machine-readable output
        response_mime_type="application/json",

        # 🎯 Deterministic output (best for schemas)
        temperature=0.0,


        # 🚫 Reduce refusals / partial responses
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.OFF,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
        ],
    )



async def create_session(session_service_stateful , app_name: str, user_id: str, session_id: int , intitial_state: dict):
    """Create a session for the user"""
    await session_service_stateful.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=intitial_state
    )


async def create_runner(agent, app_name, session_service_stateful):
    """Create a runner for the agent"""
    return Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service_stateful
    )


async def create_prompt():
    """Create a prompt for the agent"""
    return types.Content(
        role="user",
        parts=[types.Part(
            text="Based on the provided SRS data, generate the SRS document as per the schema."
        )]
    )


async def create_prompt(
    project_name: str,
    problem_statement: str,
    section_type: str
) -> types.Content:
    

    if section_type == "CORE_FEATURES":
        text = f"""
Based on the following project information, generate the core features.

Project Name: {project_name}
Problem Statement: {problem_statement}

Instructions:
- Generate 4-12 essential core features
- Each feature must be clear, concise, and focused on a single functionality
- Use present tense
- Keep each feature within 5-10 words
- Do NOT include explanations or headings

Output Requirements:
- Return ONLY valid JSON
- JSON must strictly match the CORE_FEATURES_Section schema
"""
    elif section_type == "PRIMARY_USER_FLOW":
        text = f"""
Based on the following project information, generate the primary user flow.

Project Name: {project_name}
Problem Statement: {problem_statement}

Instructions:
- Describe the complete end-to-end user journey
- Start from entry/login and end at final output or exit
- Include all major user actions and system responses
- Keep the flow logical and sequential

Output Requirements:
- Return ONLY valid JSON
- JSON must strictly match the PRIMARY_USER_FLOW_Section schema
"""
    else:
        raise ValueError(f"Unsupported section type: {section_type}")

    return types.Content(
        role="user",
        parts=[types.Part(text=text.strip())]
    )


async def generated_response(runner, user_id, session_id, prompt):
    response = None
    async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=prompt,
            ):
                if event.is_final_response():
                    # print("Final response received: ", event.content.parts[0].text)
                    response = event.content.parts[0].text

    return response


def clean_and_parse_json(raw_response):
    if isinstance(raw_response, dict):
        return raw_response
    
    if not isinstance(raw_response, str):
        return None

    cleaned = raw_response.strip()
    
    # 1. Remove Markdown Code Blocks
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            cleaned = re.sub(r"[\x00-\x1F\x7F]", " ", cleaned) 
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON string: {e}")
            return None


async def get_session(session_service_stateful ,app_name , user_id , session_id):
    """Get the session for the user"""
    return await session_service_stateful.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    



def sanitize_mermaid_output(text: str) -> str | None:
    if not text or not isinstance(text, str):
        return None

    lowered = text.lower()

    refusal_markers = [
        "i can't help",
        "i cannot help",
        "sorry",
        "unable to",
        "as an ai",
        "cannot generate"
    ]
    if any(marker in lowered for marker in refusal_markers):
        return None

    # Remove markdown fences
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*", "", text)
    text = re.sub(r"```$", "", text)

    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Normalize labeled arrows
        line = re.sub(
            r"(.*?)-->\s*\|\s*(.*?)\s*\|\s*(.*)",
            r"\1-->| \2 | \3",
            line
        )

        # Normalize arrow variants
        line = re.sub(r"-{3,}>", "-->", line)
        line = re.sub(r"<-{3,}", "<--", line)
        line = re.sub(r"==>", "-->", line)

        cleaned_lines.append(line)

    if not cleaned_lines:
        return None

    first = cleaned_lines[0]
    valid_headers = (
        "flowchart", "graph", "erDiagram",
        "sequenceDiagram", "stateDiagram", "classDiagram"
    )

    if not first.startswith(valid_headers):
        cleaned_lines.insert(0, "flowchart LR")

    return "\n".join(cleaned_lines)




def clean_interface_diagrams(external_interfaces: dict) -> dict:
    """
    Iterates through the external_interfaces dictionary, cleans the mermaid code 
    for each interface type, and returns the updated dictionary.
    """
    # Define the keys to check within the dictionary
    interface_keys = [
        "user_interfaces",
        "hardware_interfaces",
        "software_interfaces",
        "communication_interfaces"
    ]

    for key in interface_keys:
        # Check if the key and the nested path exist to avoid KeyErrors
        try:
            raw_code = external_interfaces[key]["interface_diagram"]["code"]
            
            # Use your existing sanitize function
            cleaned_code = sanitize_mermaid_output(raw_code)
            
            if cleaned_code:
                # Store the cleaned code back into the dictionary
                external_interfaces[key]["interface_diagram"]["code"] = cleaned_code
            else:
                # Optional: Provide a minimal valid fallback if sanitization returns None
                external_interfaces[key]["interface_diagram"]["code"] = "flowchart LR\n    N/A[No Interface Defined]"
        
        except (KeyError, TypeError):
            # Skip if the specific interface section is missing from the input
            continue

    return external_interfaces




def render_mermaid_png(mermaid_code: str, output_png: Path):
    """
    Renders Mermaid code into a PNG file using mmdc (npm).
    """
    import os
    import ctypes
    from ctypes import wintypes
    import platform
    
    def get_short_path(long_path):
        """Convert long path to Windows short path (8.3 format)"""
        if platform.system() != 'Windows':
            return long_path
            
        _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
        _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        _GetShortPathNameW.restype = wintypes.DWORD
        
        output_buf_size = 0
        while True:
            output_buf = ctypes.create_unicode_buffer(output_buf_size)
            needed = _GetShortPathNameW(long_path, output_buf, output_buf_size)
            if output_buf_size >= needed:
                return output_buf.value if output_buf.value else long_path
            else:
                output_buf_size = needed
    
    # Check if mmdc is available
    mmdc_path = shutil.which("mmdc")
    if not mmdc_path:
        # Try to find it in npm global directory
        if platform.system() == 'Windows':
            npm_mmdc = os.path.join(os.environ.get('APPDATA', ''), 'npm', 'mmdc.CMD')
            if os.path.exists(npm_mmdc):
                mmdc_path = npm_mmdc
        
        if not mmdc_path:
            raise FileNotFoundError(
                "mmdc command not found. Please install it using: npm install -g @mermaid-js/mermaid-cli"
            )
    
    # Convert to short path on Windows to handle spaces
    if platform.system() == 'Windows':
        mmdc_path = get_short_path(mmdc_path)
    
    output_png.parent.mkdir(parents=True, exist_ok=True)
    mmd_path = output_png.with_suffix(".mmd")

    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_code)

    cmd = [
        mmdc_path,
        "-i", str(mmd_path),
        "-o", str(output_png),
        "-w", "2400",
        "-H", "1600",
        "-t", "forest",
        "-b", "white",
        "-s", "2"
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Mermaid diagram saved: {output_png}")
    except subprocess.CalledProcessError as e:
        print(f"❌ mmdc error: {e.stderr}")
        raise


from google.genai import types

async def create_enhance_prompt(
    project_name: str,
    problem_statement: str
) -> types.Content:
    """
    Create the prompt for the enhance problem statement agent.
    """

    text = f"""
Based on the following project information, enhance the problem statement.

Project Name: {project_name}
Current Problem Statement: {problem_statement}

Instructions:
- Rewrite the problem statement in an enhanced form
- Make it specific, measurable, and outcome-driven
- Identify key stakeholders
- Define clear success metrics
- Specify relevant timeframes
- Clearly explain business value and expected impact
- Keep the enhanced statement concise and well-structured (50–1000 characters)

Output Requirements:
- Return ONLY valid JSON
- JSON must strictly match the EnhancedProblemStatementSection schema
- Include only the `enhanced_problem_statement` field
- Do NOT include explanations, markdown, or additional text
"""

    return types.Content(
        role="user",
        parts=[types.Part(text=text.strip())]
    )
