"""
GitHub Repository Analyzer
Analyzes repositories and generates insights about activity, complexity, and learning difficulty
"""

import requests
from typing import Dict, List, Tuple, Optional
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class RepositoryAnalyzer:
    \"\"\"Main analyzer class\"\"\"
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.base_url = "https://api.github.com"
        self.cache = {}
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    def analyze(self, owner: str, repo: str) -> Dict:
        \"\"\"
        Main analysis method
        
        Args:
            owner: Repository owner username
            repo: Repository name
            
        Returns:
            Dictionary with complete analysis
        \"\"\"
        
        # Fetch repository data
        repo_data = self._fetch_repo_data(owner, repo)
        
        if not repo_data:
            return {
                "error": f"Repository not found: {owner}/{repo}",
                "repo": f"{owner}/{repo}"
            }
        
        # Extract key metrics
        metrics = self._extract_metrics(owner, repo, repo_data)
        
        # Calculate scores
        activity_score, activity_details = self._calculate_activity_score(metrics)
        complexity_score, complexity_details = self._calculate_complexity_score(metrics)
        difficulty, difficulty_reason = self._classify_difficulty(activity_score, complexity_score)
        
        # Build result
        result = {
            "repository": f"{owner}/{repo}",
            "url": repo_data.get("html_url"),
            "description": repo_data.get("description", "No description"),
            
            "activity_score": activity_score,
            "activity_details": activity_details,
            
            "complexity_score": complexity_score,
            "complexity_details": complexity_details,
            
            "learning_difficulty": difficulty,
            "difficulty_reason": difficulty_reason,
            
            "metrics": {
                "stars": metrics["stars"],
                "forks": metrics["forks"],
                "watchers": metrics["watchers"],
                "open_issues": metrics["open_issues"],
                "contributors": metrics["contributors"],
                "commits": metrics["commits"],
                "languages": metrics["languages"],
                "size_mb": round(metrics["size_kb"] / 1024, 2),
                "created_at": repo_data.get("created_at"),
                "last_updated": repo_data.get("updated_at"),
                "is_fork": repo_data.get("fork", False),
            },
            
            "recommendation": self._generate_recommendation(
                difficulty,
                activity_score,
                complexity_score,
                metrics
            )
        }
        
        return result
    
    def _fetch_repo_data(self, owner: str, repo: str) -> Optional[Dict]:
        \"\"\"Fetch repository data from GitHub API\"\"\"
        
        cache_key = f"{owner}/{repo}:repo_data"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 404:
                return None
            elif response.status_code == 403:
                raise Exception("Rate limit exceeded or access denied")
            elif response.status_code != 200:
                raise Exception(f"GitHub API error: {response.status_code}")
            
            data = response.json()
            self.cache[cache_key] = data
            return data
            
        except requests.exceptions.Timeout:
            raise Exception("Request timed out")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
    
    def _extract_metrics(self, owner: str, repo: str, repo_data: Dict) -> Dict:
        \"\"\"Extract key metrics from repository data\"\"\"
        
        # Get contributors count
        contributors = self._get_contributors_count(owner, repo)
        
        # Get commits count
        commits = self._get_commits_count(owner, repo)
        
        # Get languages
        languages = self._get_languages(owner, repo)
        
        return {
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "watchers": repo_data.get("watchers_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "contributors": contributors,
            "commits": commits,
            "languages": languages,
            "size_kb": repo_data.get("size", 0),
            "is_fork": repo_data.get("fork", False),
            "created_at": repo_data.get("created_at"),
            "updated_at": repo_data.get("updated_at"),
        }
    
    def _get_contributors_count(self, owner: str, repo: str) -> int:
        \"\"\"Get contributors count\"\"\"
        
        cache_key = f"{owner}/{repo}:contributors"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{self.base_url}/repos/{owner}/{repo}/contributors"
        
        try:
            # Request with per_page=1 to get total from headers
            response = requests.get(
                url,
                headers=self.headers,
                params={"per_page": 1},
                timeout=10
            )
            
            if response.status_code not in [200, 304]:
                return 0
            
            # GitHub returns total count in Link header if pagination exists
            if "Link" in response.headers:
                import re
                link = response.headers["Link"]
                match = re.search(r'page=(\\\\d+)>; rel="last"', link)
                if match:
                    count = int(match.group(1))
                    self.cache[cache_key] = count
                    return count
            
            # If no pagination header, it's less than per_page
            data = response.json()
            count = len(data) if isinstance(data, list) else 1
            self.cache[cache_key] = count
            return count
            
        except Exception:
            return 0
    
    def _get_commits_count(self, owner: str, repo: str) -> int:
        \"\"\"Get commits count\"\"\"
        
        cache_key = f"{owner}/{repo}:commits"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={"per_page": 1},
                timeout=10
            )
            
            if response.status_code not in [200, 304]:
                return 0
            
            # GitHub returns total count in Link header
            if "Link" in response.headers:
                import re
                link = response.headers["Link"]
                match = re.search(r'page=(\\\\d+)>; rel="last"', link)
                if match:
                    count = int(match.group(1))
                    self.cache[cache_key] = count
                    return count
            
            # Fallback
            self.cache[cache_key] = 1
            return 1
            
        except Exception:
            return 0
    
    def _get_languages(self, owner: str, repo: str) -> List[str]:
        \"\"\"Get list of programming languages\"\"\"
        
        cache_key = f"{owner}/{repo}:languages"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{self.base_url}/repos/{owner}/{repo}/languages"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            languages = list(data.keys()) if data else []
            self.cache[cache_key] = languages
            return languages
            
        except Exception:
            return []
    
    def _calculate_activity_score(self, metrics: Dict) -> Tuple[int, Dict]:
        \"\"\"
        Calculate activity score (0-100)
        
        Based on:
        - Stars (popularity)
        - Commits (development activity)
        - Contributors (community size)
        - Open issues (active development)
        \"\"\"
        
        # Normalize each metric to 0-25 points
        
        # Stars: 0 = 0pts, 50k+ = 25pts
        stars = metrics["stars"]
        if stars >= 50000:
            stars_score = 25
        else:
            stars_score = min(25, (stars / 50000) * 25)
        
        # Commits: 0 = 0pts, 50k+ = 25pts
        commits = metrics["commits"]
        if commits >= 50000:
            commits_score = 25
        else:
            commits_score = min(25, (commits / 50000) * 25)
        
        # Contributors: 0 = 0pts, 2k+ = 25pts
        contributors = metrics["contributors"]
        if contributors >= 2000:
            contributors_score = 25
        else:
            contributors_score = min(25, (contributors / 2000) * 25)
        
        # Open issues: 0 = 0pts, 5k+ = 25pts
        issues = metrics["open_issues"]
        if issues >= 5000:
            issues_score = 25
        else:
            issues_score = min(25, (issues / 5000) * 25)
        
        total_score = int(stars_score + commits_score + contributors_score + issues_score)
        total_score = min(100, total_score)
        
        # Determine activity level
        if total_score >= 80:
            level = "Very Active"
        elif total_score >= 60:
            level = "Active"
        elif total_score >= 40:
            level = "Moderately Active"
        elif total_score >= 20:
            level = "Lightly Active"
        else:
            level = "Inactive"
        
        details = {
            "level": level,
            "stars_contribution": round(stars_score, 1),
            "commits_contribution": round(commits_score, 1),
            "contributors_contribution": round(contributors_score, 1),
            "issues_contribution": round(issues_score, 1),
            "summary": f"{level} project with {stars} stars, {commits} commits, {contributors} contributors, and {issues} open issues"
        }
        
        return total_score, details
    
    def _calculate_complexity_score(self, metrics: Dict) -> Tuple[int, Dict]:
        \"\"\"
        Calculate complexity score (0-100)
        
        Based on:
        - Repository size (code volume)
        - Number of languages (architectural diversity)
        - Language sophistication
        - Contributor count (proxy for codebase complexity)
        \"\"\"
        
        # Size: 0KB = 0pts, 500MB+ = 25pts
        size_mb = metrics["size_kb"] / 1024
        if size_mb >= 500:
            size_score = 25
        else:
            size_score = min(25, (size_mb / 500) * 25)
        
        # Language diversity: 1 lang = 0pts, 10+ langs = 30pts
        num_languages = len(metrics["languages"])
        if num_languages >= 10:
            language_score = 30
        else:
            language_score = min(30, (num_languages / 10) * 30)
        
        # Language sophistication
        complexity_languages = {
            "Rust": 4, "C++": 4, "Scala": 4,
            "Go": 3, "C": 3, "Java": 3, "Kotlin": 3,
            "TypeScript": 2, "Python": 2,
            "JavaScript": 1, "Ruby": 1, "PHP": 1
        }
        
        sophistication_score = 0
        for lang in metrics["languages"]:
            if lang in complexity_languages:
                sophistication_score += complexity_languages[lang]
        sophistication_score = min(25, sophistication_score)
        
        # Contributor count: 0 = 0pts, 500+ = 20pts
        contributors = metrics["contributors"]
        if contributors >= 500:
            contributor_score = 20
        else:
            contributor_score = min(20, (contributors / 500) * 20)
        
        total_score = int(size_score + language_score + sophistication_score + contributor_score)
        total_score = min(100, total_score)
        
        # Determine complexity level
        if total_score >= 75:
            level = "Very Complex"
        elif total_score >= 50:
            level = "Moderately Complex"
        elif total_score >= 25:
            level = "Relatively Simple"
        else:
            level = "Very Simple"
        
        size_mb_rounded = round(size_mb, 1)
        details = {
            "level": level,
            "size_contribution": round(size_score, 1),
            "language_diversity_contribution": round(language_score, 1),
            "language_sophistication_contribution": round(sophistication_score, 1),
            "contributor_contribution": round(contributor_score, 1),
            "summary": f"{level} codebase: {size_mb_rounded}MB, {num_languages} languages ({', '.join(metrics['languages'][:5])}{'...' if num_languages > 5 else ''})"
        }
        
        return total_score, details
    
    def _classify_difficulty(self, activity_score: int, complexity_score: int) -> Tuple[str, str]:
        \"\"\"
        Classify learning difficulty
        
        - Beginner: Low complexity (<35) AND low-moderate activity (<50)
        - Intermediate: Medium values OR moderate complexity with active development
        - Advanced: High complexity (>65) OR very active (>75)
        \"\"\"
        
        if complexity_score < 35 and activity_score < 50:
            # Simple + not very active = Beginner
            difficulty = "Beginner"
            reason = (
                f"This is a great repository for beginners. "
                f"It has a relatively simple codebase ({complexity_score}/100 complexity) "
                f"and moderate activity level ({activity_score}/100 activity). "
                f"The codebase is manageable and the pace of changes is not overwhelming, "
                f"making it ideal for learning and making your first contributions."
            )
        
        elif complexity_score >= 65 or activity_score >= 75:
            # Complex OR very active = Advanced
            difficulty = "Advanced"
            if complexity_score >= 65 and activity_score >= 75:
                reason = (
                    f"This is an advanced repository. "
                    f"It combines high complexity ({complexity_score}/100) with very active development ({activity_score}/100). "
                    f"This project requires deep software engineering knowledge, experience with collaborative development, "
                    f"and ability to navigate complex codebases. Recommended for experienced developers."
                )
            elif complexity_score >= 65:
                reason = (
                    f"This is an advanced repository due to its high complexity ({complexity_score}/100). "
                    f"The codebase has significant architectural sophistication and requires strong software engineering fundamentals. "
                    f"Recommended for developers with solid experience in the project's domain."
                )
            else:
                reason = (
                    f"This is an advanced repository due to its very high activity level ({activity_score}/100). "
                    f"Contributing requires keeping up with rapid development cycles and managing conflicts with many active developers. "
                    f"Recommended for experienced developers comfortable with collaborative workflows."
                )
        
        else:
            # Middle ground = Intermediate
            difficulty = "Intermediate"
            reason = (
                f"This is an intermediate-level repository. "
                f"It has moderate complexity ({complexity_score}/100) and reasonable activity level ({activity_score}/100). "
                f"It's suitable for developers who have some experience and want to challenge themselves. "
                f"You should understand basic software design patterns and be comfortable working in teams."
            )
        
        return difficulty, reason
    
    def _generate_recommendation(
        self,
        difficulty: str,
        activity_score: int,
        complexity_score: int,
        metrics: Dict
    ) -> str:
        \"\"\"Generate personalized recommendation based on analysis\"\"\"
        
        recommendations = []
        
        # Based on difficulty
        if difficulty == "Beginner":
            recommendations.append(
                "✓ Excellent for first-time contributors to understand open source"
            )
            recommendations.append(
                "✓ Good starting point to learn about the project domain"
            )
            if metrics["open_issues"] > 0:
                recommendations.append(
                    f"✓ {metrics['open_issues']} open issues available for beginners to tackle"
                )
        
        elif difficulty == "Intermediate":
            recommendations.append(
                "✓ Suitable for developers looking to expand their skills"
            )
            recommendations.append(
                "✓ Good opportunity to work with larger teams"
            )
            if activity_score >= 60:
                recommendations.append(
                    "✓ Active development means your contributions will be reviewed quickly"
                )
        
        else:  # Advanced
            recommendations.append(
                "✓ Ideal for experienced developers wanting to work on cutting-edge projects"
            )
            recommendations.append(
                "✓ Requires commitment to stay current with rapid changes"
            )
            if metrics["contributors"] >= 100:
                recommendations.append(
                    f"✓ Large community ({metrics['contributors']}+ contributors) means good support"
                )
        
        # Based on popularity
        if metrics["stars"] >= 10000:
            recommendations.append(
                "✓ Highly popular - great for your resume and GitHub profile"
            )
        
        return " | ".join(recommendations)

