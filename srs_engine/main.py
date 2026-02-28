from __future__ import annotations

"""
SRS_Engine FastAPI entrypoint.

This module was refactored to register routers from `srs_engine/core/routers/`,
set up centralized logging, configure MongoDB, and enable cookie sessions.

The legacy monolithic implementation is preserved below (disabled) to avoid
deleting existing code while keeping runtime behavior clean and production-ready.
"""

from contextlib import asynccontextmanager
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.adk.sessions import InMemorySessionService
from starlette.middleware.sessions import SessionMiddleware

from srs_engine.core.config import get_settings
from srs_engine.core.db.mongo import init_mongo
from srs_engine.core.logging import get_logger
from srs_engine.core.logging.config import setup_logging
from srs_engine.core.routers import auth_router, contact_router, pages_router, srs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB
    settings = get_settings()
    logger = get_logger("srs_engine.main")
    logger.info("Initializing MongoDB connection")
    await init_mongo(app, settings)
    yield
    # Shutdown: Cleanup if needed
    logger.info("Shutting down SRS_Engine")


def create_app() -> FastAPI:
    load_dotenv(find_dotenv())
    settings = get_settings()

    setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)
    logger = get_logger("srs_engine.main")
    logger.info("Starting SRS_Engine")

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        same_site="lax",
        https_only=False,
    )

    app.mount("/static", StaticFiles(directory="srs_engine/static"), name="static")

    app.state.templates = Jinja2Templates(directory="srs_engine/templates")
    app.state.session_service_stateful = InMemorySessionService()

    app.include_router(pages_router)
    app.include_router(auth_router)
    app.include_router(srs_router)
    app.include_router(contact_router)

    return app


app = create_app()

"""
LEGACY IMPLEMENTATION (disabled)

from http.client import HTTPException
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.adk.sessions import InMemorySessionService
from google.adk.agents import SequentialAgent , ParallelAgent
import json
import uuid
from srs_engine.agents.technical_srs_agents.introduction_agent import create_introduction_agent as create_technical_srs_introduction_agent
from srs_engine.agents.technical_srs_agents.overall_description_agent import create_overall_description_agent as create_technical_srs_overall_description_agent
from srs_engine.agents.technical_srs_agents.system_features_agent import create_system_features_agent as create_technical_srs_system_features_agent
from srs_engine.agents.technical_srs_agents.external_interfaces_agent import create_external_interfaces_agent as create_technical_srs_external_interfaces_agent
from srs_engine.agents.technical_srs_agents.nfr_agent import create_nfr_agent as create_technical_srs_nfr_agent
from srs_engine.agents.technical_srs_agents.glossary_agent import create_glossary_agent as create_technical_srs_glossary_agent
from srs_engine.agents.technical_srs_agents.assumptions_agent import create_assumptions_agent as create_technical_srs_assumptions_agent
from srs_engine.agents.home_page_agents.auto_generate_agent import create_auto_generate_agent
from srs_engine.schemas.home_page_schemas.srs_input_schema import SRSRequest
from srs_engine.schemas.home_page_schemas.auto_generate_input_schema import AutoGenerateInput
from srs_engine.schemas.home_page_schemas.problem_statement_enhance_schema import EnhanceProblemStatementInput
from srs_engine.agents.home_page_agents.enhance_problem_statement_agent import create_enhance_problem_statement_agent
from srs_engine.utils.globals import (
    create_session , 
    create_runner , 
    create_prompt , 
    generated_response , 
    get_session , 
    clean_and_parse_json,
    clean_interface_diagrams,
    render_mermaid_png ,
    create_prompt ,
    create_enhance_prompt)
from pathlib import Path
import time
from datetime import datetime
from srs_engine.utils.srs_document_generator import generate_srs_document

today = datetime.today().strftime("%m/%d/%Y")

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory="srs_engine/static"),
    name="static"
)


templates = Jinja2Templates(directory="srs_engine/templates")

session_service_stateful = InMemorySessionService()

async def create_technical_srs_agent():
     
    first_agent = SequentialAgent(
          name = "first_agent",
          sub_agents = [
               ParallelAgent(
                    name = "first_parallel_agent",
                    sub_agents = [
                         create_technical_srs_introduction_agent(),
                         create_technical_srs_overall_description_agent(),
                         create_technical_srs_system_features_agent(),
                         create_technical_srs_external_interfaces_agent(),
                         create_technical_srs_nfr_agent()
                    ],
                    description = "This agent handles the generation of the Introduction and Overall Description sections of the SRS document."
               )
          ]
     )

    second_agent = SequentialAgent(
          name = "second_agent",
          sub_agents = [
               ParallelAgent(
                   name = "finalization_agent",
                   sub_agents = [
                       create_technical_srs_glossary_agent(),
                       create_technical_srs_assumptions_agent()
                   ],
                   description = "This agent handles the generation of the Glossary and Assumptions sections of the SRS document."
               )
          ]
     )

    
    return first_agent , second_agent




@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": request}
    )


@app.post("/enhance-problem-statement")
async def enhance_problem_statement(input_data: EnhanceProblemStatementInput):
    try:
        print(f"Received enhance problem request: {input_data}")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Extract input data
        inputs = input_data.dict()
        project_name = inputs["project_name"]
        problem_statement = inputs["problem_statement"]
        
        print(f"Enhancing problem statement for project: {project_name}")
        
        # User ID (in production, get from authentication)
        user_id = "test"
        
        # Create initial state for session
        initial_state = {
            "project_name": project_name,
            "problem_statement": problem_statement,
            "section_type": "PROBLEM_STATEMENT_ENHANCEMENT"
        }
        
        # Create session
        await create_session(
            session_service_stateful,
            project_name,
            user_id,
            session_id,
            initial_state
        )
        print(f"Session created with ID: {session_id}")
        
        # Create enhance problem statement agent
        enhance_agent = create_enhance_problem_statement_agent()
        print("Enhance problem agent created")
        
        # Create runner
        runner = await create_runner(
            enhance_agent,
            project_name,
            session_service_stateful
        )
        print("Runner created for agent")
        
        # Create prompt
        prompt = await create_enhance_prompt(project_name, problem_statement)
        # print(f"Prompt created: {prompt[:100]}...")
        
        # Generate response
        response = await generated_response(runner, user_id, session_id, prompt)
        print(f"Response generated by agent: {response}")
        
        # Parse the JSON string response
        try:
            # If response is a string, parse it as JSON
            if isinstance(response, str):
                parsed_response = json.loads(response)
            elif isinstance(response, dict):
                parsed_response = response
            else:
                # Try to convert to dict if it's an object with attributes
                parsed_response = response.dict() if hasattr(response, 'dict') else dict(response)
            
            print(f"Parsed response: {parsed_response}")
            
            # Validate the response has the required field
            if "enhanced_problem_statement" not in parsed_response:
                raise ValueError("Response missing 'enhanced_problem_statement' key")
            
            enhanced_statement = parsed_response["enhanced_problem_statement"]
            
            # Validate length
            if not isinstance(enhanced_statement, str):
                raise ValueError("'enhanced_problem_statement' must be a string")
            
            if len(enhanced_statement) < 50:
                raise ValueError("Enhanced problem statement is too short (minimum 50 characters)")
            
            if len(enhanced_statement) > 1000:
                raise ValueError("Enhanced problem statement is too long (maximum 1000 characters)")
            
            # Return the enhanced problem statement
            return {"enhanced_problem_statement": enhanced_statement}
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse agent response: {str(e)}"
            )
        except ValueError as e:
            print(f"Validation error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Invalid response format: {str(e)}"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        print(f"Error in enhance_problem_statement: {str(e)}")



@app.post("/auto-generate-section")
async def auto_generate_section(input_data: AutoGenerateInput):
    print("Received auto-generate request: ", input_data)
    session_id = str(uuid.uuid4())

    inputs = input_data.dict()
    project_name = inputs["project_name"]
    problem_statement = inputs["problem_statement"]
    section_type = inputs["section_type"]

    if section_type == "features":
        internal_section_type = "CORE_FEATURES"
    else:
        internal_section_type = "PRIMARY_USER_FLOW"

    user_id = "test"

    initial_state = {
        "project_name": project_name,
        "problem_statement": problem_statement,
        "section_type": internal_section_type
    }

    await create_session(session_service_stateful, project_name, user_id, session_id, initial_state)
    print("Session created with ID: ", session_id)

    auto_generate_agent = create_auto_generate_agent(internal_section_type)
    runner = await create_runner(auto_generate_agent, project_name, session_service_stateful)
    print("Runner created for agent")

    prompt = await create_prompt(project_name, problem_statement, internal_section_type)
    print("Prompt created for agent")

    response = await generated_response(runner, user_id, session_id, prompt)
    print(f"Response generated by agent: {response}")

    # Parse and format the response
    try:
        # Parse JSON string to dict
        if isinstance(response, str):
            data = json.loads(response)
        else:
            data = response if isinstance(response, dict) else response.dict()
        
        # Validate and return based on section type
        if section_type == "features":
            if "core_features" not in data:
                raise ValueError("Response missing 'core_features' key")
            if not isinstance(data["core_features"], list):
                raise ValueError("'core_features' must be a list")
            if len(data["core_features"]) < 4:
                raise ValueError("Must have at least 4 features")
            
            return {"core_features": data["core_features"]}
        
        else:  # flow
            if "primary_user_flow" not in data:
                raise ValueError("Response missing 'primary_user_flow' key")
            if not isinstance(data["primary_user_flow"], str):
                raise ValueError("'primary_user_flow' must be a string")
            if len(data["primary_user_flow"]) < 100:
                raise ValueError("User flow must be at least 100 characters")
            
            return {"primary_user_flow": data["primary_user_flow"]}
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid JSON response: {str(e)}")
    except ValueError as e:
        print(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid response format: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
        


@app.post("/generate_srs")
async def generate_srs(srs_data: SRSRequest):


    print("Received SRS Data: ", srs_data)
    session_id = str(uuid.uuid4())

    inputs = srs_data.dict()
    project_name = inputs["project_identity"]["project_name"] # will be used later
    author_list = inputs["project_identity"]["author"] # will be used later
    organization_name = inputs["project_identity"]["organization"] # will be used later
    # model_provider = inputs["model_indentity"]["model_provider"]
    # model_api_key = inputs["model_indentity"]["model_api_key"]
    # model_name = inputs["model_indentity"]["model_name"]
    

    user_id = "test"  # In real scenarios, fetch from auth system

    initial_state = { "user_inputs": inputs }

    print(f'''Project Name: {project_name}''')
    print(f'''Authors: {author_list}''')
    print(f'''Organization: {organization_name}''')
    print(f'Initial state: {initial_state}')

    await create_session(session_service_stateful, project_name, user_id, session_id , initial_state)

    print("Session created with ID: ", session_id)

    first_agent , second_agent  = await create_technical_srs_agent()
    runner = await create_runner(first_agent, project_name, session_service_stateful)

    print("Runner created for agent ")
    prompt = await create_prompt()

    print("Prompt created for agent ")

    response = await generated_response(runner , user_id , session_id , prompt)

    print("Response generated by agent ")

    session = await get_session(session_service_stateful,project_name , user_id , session_id)

    print("Session state after agent run: ", session.state)
    
    time.sleep(60) 

    second_runner = await create_runner(second_agent, project_name, session_service_stateful)   
    
    print(f"Second Runner created for agent ")

    second_response = await generated_response(second_runner , user_id , session_id , prompt)

    print("Response generated by second agent ")

    session = await get_session(session_service_stateful,project_name , user_id , session_id)

    print("Session state after second agent run: ", session.state)
    

    introduction_section = clean_and_parse_json(session.state.get("introduction_section", {}))
    print("Introduction Section: ", introduction_section)
    overall_description_section = clean_and_parse_json(session.state.get("overall_description_section", {}))
    print("Overall Description Section: ", overall_description_section)
    system_features_section = clean_and_parse_json(session.state.get("system_features_section", {}))
    print("System Features Section: ", system_features_section)
    external_interfaces_section = clean_interface_diagrams(clean_and_parse_json(session.state.get("external_interfaces_section", {})))
    print("External Interfaces Section: ", external_interfaces_section)

    base_dir = Path("./srs_engine/generated_images") / project_name
    base_dir.mkdir(parents=True, exist_ok=True)

    image_paths = {
    "user_interfaces": base_dir / f"{project_name}_user_interfaces_diagram.png",
    "hardware_interfaces": base_dir / f"{project_name}_hardware_interfaces_diagram.png",
    "software_interfaces": base_dir / f"{project_name}_software_interfaces_diagram.png",
    "communication_interfaces": base_dir / f"{project_name}_communication_interfaces_diagram.png",
}


    render_mermaid_png(external_interfaces_section['user_interfaces']['interface_diagram']['code'], image_paths['user_interfaces'])
    render_mermaid_png(external_interfaces_section['hardware_interfaces']['interface_diagram']['code'], image_paths['hardware_interfaces'])
    render_mermaid_png(external_interfaces_section['software_interfaces']['interface_diagram']['code'], image_paths['software_interfaces'])
    render_mermaid_png(external_interfaces_section['communication_interfaces']['interface_diagram']['code'], image_paths['communication_interfaces'])




    nfr_section = clean_and_parse_json(session.state.get("nfr_section", {}))
    print("Non-Functional Requirements Section: ", nfr_section)


    glossary_section = clean_and_parse_json(session.state.get("glossary_section", {}))
    print("Glossary Section: ", glossary_section)


    assumptions_section = clean_and_parse_json(session.state.get("assumptions_section", {}))
    print("Assumptions Section: ", assumptions_section)


    ## SRS Making ##
    output_path = f"./srs_engine/generated_srs/{project_name}_SRS.docx"

    Path("./srs_engine/generated_srs").mkdir(exist_ok=True)

    generated_path = generate_srs_document(
        project_name=project_name,
        introduction_section=introduction_section,
        overall_description_section=overall_description_section,
        system_features_section=system_features_section,
        external_interfaces_section=external_interfaces_section,
        nfr_section=nfr_section,
        glossary_section=glossary_section,
        assumptions_section=assumptions_section,
        image_paths=image_paths,
        output_path=output_path,
        authors=author_list , # List of authors
        organization=organization_name
    )

    print(f"✅ SRS document generated successfully: {generated_path}")




    return {
        "srs_document_path": generated_path
    }

"""












