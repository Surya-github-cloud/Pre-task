"""
GitHub Repository Intelligence Analyzer
FastAPI Application
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
from analyzer import RepositoryAnalyzer

# Initialize FastAPI app
app = FastAPI(
    title="GitHub Repository Intelligence Analyzer",
    description="Analyze GitHub repositories for activity, complexity, and learning difficulty",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize analyzer
analyzer = RepositoryAnalyzer()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with UI"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api", tags=["Info"])
async def api_info():
    """API Information"""
    return {
        "name": "GitHub Repository Intelligence Analyzer",
        "version": "1.0.0",
        "description": "Analyze GitHub repositories for insights",
        "endpoints": {
            "analyze_single": "/analyze?repo=owner/repo",
            "analyze_batch": "/analyze-batch?repos=owner/repo1,owner/repo2",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.get("/analyze", tags=["Analysis"])
async def analyze(
    repo: str = Query(..., description="Repository in format 'owner/repo'", example="facebook/react")
):
    """
    Analyze a GitHub repository
    
    Returns:
    - activity_score: How active/maintained (0-100)
    - complexity_score: Code complexity (0-100)
    - learning_difficulty: Beginner/Intermediate/Advanced
    - metrics: Repository statistics
    - recommendation: Personalized recommendation
    """
    
    try:
        # Validate input
        if "/" not in repo:
            raise ValueError("Repository must be in format 'owner/repo'")
        
        parts = repo.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("Invalid repository format")
        
        owner, repo_name = parts
        
        # Analyze
        result = analyzer.analyze(owner, repo_name)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        
        if "not found" in error_msg.lower():
            status_code = 404
        elif "rate limit" in error_msg.lower():
            status_code = 429
        elif "timeout" in error_msg.lower():
            status_code = 504
        
        raise HTTPException(status_code=status_code, detail=error_msg)


@app.get("/analyze-batch", tags=["Analysis"])
async def analyze_batch(
    repos: str = Query(..., description="Comma-separated repos", example="facebook/react,tensorflow/tensorflow")
):
    """
    Analyze multiple repositories at once
    
    Maximum 10 repositories per request
    """
    
    try:
        repo_list = [r.strip() for r in repos.split(",")]
        
        if len(repo_list) > 10:
            raise ValueError("Maximum 10 repositories per request")
        
        results = []
        for repo in repo_list:
            try:
                if "/" not in repo:
                    results.append({
                        "error": f"Invalid format: {repo}",
                        "repo": repo
                    })
                    continue
                
                owner, repo_name = repo.split("/", 1)
                result = analyzer.analyze(owner, repo_name)
                results.append(result)
                
            except Exception as e:
                results.append({
                    "error": str(e),
                    "repo": repo
                })
        
        return {
            "count": len(results),
            "repositories": results
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/cache", tags=["Info"])
async def cache_info():
    """Get cache statistics"""
    return {
        "cached_items": len(analyzer.cache),
        "cache_keys": list(analyzer.cache.keys())[:10]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

