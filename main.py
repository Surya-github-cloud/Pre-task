"""
GitHub Repository Intelligence Analyzer
FastAPI Application - Vercel Compatible
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from analyzer import RepositoryAnalyzer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = RepositoryAnalyzer()


@app.get("/")
async def root():
    return {
        "name": "GitHub Repository Intelligence Analyzer",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/analyze?repo=owner/repo",
            "batch": "/analyze-batch?repos=repo1,repo2",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/analyze")
async def analyze(
    repo: str = Query(..., description="Repository in format 'owner/repo'", example="facebook/react")
):
    try:
        if "/" not in repo:
            raise ValueError("Repository must be in format 'owner/repo'")
        
        owner, repo_name = repo.split("/", 1)
        result = analyzer.analyze(owner, repo_name)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze-batch")
async def analyze_batch(
    repos: str = Query(..., description="Comma-separated repos", example="facebook/react,tensorflow/tensorflow")
):
    try:
        repo_list = [r.strip() for r in repos.split(",")]
        
        if len(repo_list) > 10:
            raise ValueError("Maximum 10 repositories per request")
        
        results = []
        for repo in repo_list:
            try:
                if "/" not in repo:
                    results.append({"error": f"Invalid format: {repo}", "repo": repo})
                    continue
                
                owner, repo_name = repo.split("/", 1)
                result = analyzer.analyze(owner, repo_name)
                results.append(result)
                
            except Exception as e:
                results.append({"error": str(e), "repo": repo})
        
        return {"count": len(results), "repositories": results}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

