# app.py
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Header
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
import logging
from datetime import datetime
import traceback  # <-- Add this to catch full code tracebacks
from utils import convert_image_to_base64_and_test

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Universal Multi-Crop Leaf Disease API Mesh", version="2.0.0")

@app.post('/disease-detection-file')
async def disease_detection_file(
    file: UploadFile = File(...),
    crop_context: str = Header("generic")
):
    """
    Decoupled computer vision microservice interface.
    Catches exact internal processing exceptions to trace why utils.py fails.
    """
    try:
        logger.info(f"Ingesting binary stream for file: '{file.filename}' assigned under context: '{crop_context}'")
        
        # Read incoming data chunks asynchronously
        contents = await file.read()
        
        # Run model processing inside background worker threads
        try:
            result = await run_in_threadpool(convert_image_to_base64_and_test, contents)
        except Exception as model_err:
            # Captures exact code level crash inside utils.py
            error_trace = traceback.format_exc()
            logger.error(f"Crash detected inside utils.py processing logic:\n{error_trace}")
            raise HTTPException(
                status_code=500, 
                detail=f"Crash inside utils.py code line: {str(model_err)}. Full Traceback:\n{error_trace}"
            )
        
        # Check if the function executed but returned None values
        if result is None:
            logger.error("convert_image_to_base64_and_test returned None instead of a dictionary array.")
            raise HTTPException(
                status_code=500, 
                detail="The image processing utility function (utils.py) returned None. Verify your model weights loading lines."
            )
            
        # Append application scope tags into downstream JSON payloads
        result["processed_crop_context"] = crop_context.upper()
        if "analysis_timestamp" not in result:
            result["analysis_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        logger.info("Universal inference sequence finalized safely.")
        return JSONResponse(content=result)
        
    except HTTPException as http_ex:
        # Re-raise explicit HTTP exceptions to pass details directly to Streamlit
        return JSONResponse(status_code=http_ex.status_code, content={"detail": http_ex.detail})
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"General internal server exception: {str(e)}\n{error_trace}")
        return JSONResponse(
            status_code=500, 
            content={"detail": f"General System Crash: {str(e)}. Traceback:\n{error_trace}"}
        )


@app.get("/")
async def health_check():
    return {
        "microservice": "AgroNet AI Inference Cluster Node",
        "status": "Online/Healthy",
        "supported_routing_modes": "Multi-Crop Header-Driven Mesh"
    }