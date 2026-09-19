# ============================================================
# TrustLens — Main FastAPI Backend
# ============================================================

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fake_follower import analyze_fake_followers
from engagement_analyzer import analyze_engagement, analyze_comment_authenticity
from trust_score import calculate_trust_score
from data_ingestion import fetch_instagram_profile, fetch_engagement_data, fetch_post_comments
from credential_extractor import calculate_credential_confidence
import module_gateway as gateway

app = FastAPI(
    title="TrustLens API",
    description="AI-Powered Influencer Authenticity Detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "TrustLens API is running",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/services/health")
def services_health():
    """Live status of every registered module microservice."""
    return gateway.services_health()


def _misinfo_from_transcription(transcription: dict) -> dict:
    """Pull the transcript out of a transcriber job result and classify it."""
    result = (transcription or {}).get("result") or {}
    classifier_input = result.get("classifier_input") or {}
    text = classifier_input.get("text") or result.get("text") or ""
    return gateway.classify_text(text)


@app.post("/transcribe/url")
def transcribe_from_url(data: dict):
    """Standalone: transcribe a reel/video URL, then classify the transcript."""
    url = (data or {}).get("url", "")
    if not url:
        return {"error": "Please provide a url"}
    run_misinfo = (data or {}).get("run_misinfo", True)
    transcription = gateway.transcribe_url(url, wait=True)
    misinfo = _misinfo_from_transcription(transcription) if run_misinfo else None
    return {"transcription": transcription, "misinfo": misinfo}


@app.post("/transcribe/upload")
async def transcribe_from_upload(file: UploadFile = File(...), run_misinfo: bool = Form(True)):
    """Standalone: transcribe an uploaded media file, then classify the transcript."""
    content = await file.read()
    transcription = gateway.transcribe_upload(
        file.filename or "upload.mp4", content, file.content_type
    )
    misinfo = _misinfo_from_transcription(transcription) if run_misinfo else None
    return {"transcription": transcription, "misinfo": misinfo}

@app.post("/analyze")
def analyze_profile(data: dict):
    username        = data.get("username", "unknown")
    followers       = data.get("followers", 0)
    following       = data.get("following", 0)
    posts           = data.get("posts", 0)
    likes_avg       = data.get("likes_avg", 0)
    comments_avg    = data.get("comments_avg", 0)
    has_profile_pic = data.get("has_profile_pic", 1)
    bio_length      = data.get("bio_length", 0)
    has_external_url= data.get("has_external_url", 0)
    is_private      = data.get("is_private", 0)

    fake_result = analyze_fake_followers(
        followers, following, posts,
        has_profile_pic, bio_length, has_external_url, is_private
    )

    engagement_result = analyze_engagement(
        followers, likes_avg, comments_avg, posts
    )

    trust_result = calculate_trust_score(
        fake_result["bot_percentage"],
        engagement_result["engagement_score"]
    )

    return {
        "username": username,
        "fake_follower_analysis": fake_result,
        "engagement_analysis": engagement_result,
        "trust_score": trust_result
    }

@app.post("/analyze-live")
def analyze_profile_live(data: dict):
    username = data.get("username")

    if not username:
        return {"error": "Please provide a username"}

    try:
        profile = fetch_instagram_profile(username)
    except Exception as e:
        return {"error": f"Could not fetch Instagram data: {str(e)}"}

    fake_result = analyze_fake_followers(
        profile["followers"], profile["following"], profile["posts"],
        profile["has_profile_pic"], profile["bio_length"],
        profile["has_external_url"], profile["is_private"]
    )

    try:
        engagement_data = fetch_engagement_data(username)
    except Exception as e:
        return {"error": f"Could not fetch engagement data: {str(e)}"}

    engagement_result = analyze_engagement(
        profile["followers"],
        engagement_data["avg_likes"],
        engagement_data["avg_comments"],
        profile["posts"]
    )

    # ---- Comment Authenticity Check (uses most recent post) ----
    comment_authenticity = {
        "verdict": "No posts available",
        "comment_diversity_score": None,
        "campaign_keyword_detected": False
    }
    try:
        post_codes = engagement_data.get("post_codes", [])
        if post_codes:
            comments = fetch_post_comments(post_codes[0])
            comment_authenticity = analyze_comment_authenticity(comments)
    except Exception:
        pass

    # ---- Credential Extraction & Confidence Scoring ----
    credential_result = calculate_credential_confidence(
        profile.get("biography", ""), profile["is_verified"]
    )

    # ---- AI Profile-Image Detection (Module 6.7, via gateway) ----
    # Prefer the HD picture; the thumbnail is too small for a confident verdict.
    image_url = profile.get("profile_pic_url_hd") or profile.get("profile_pic_url", "")
    image_result = gateway.analyze_profile_image(image_url)
    image_risk = None
    image_band = None
    image_conf = None
    if image_result.get("status") == "ok" and image_result.get("applicable"):
        image_risk = image_result.get("score")
        image_band = image_result.get("band")
        image_conf = (image_result.get("details") or {}).get("confidence")

    trust_result = calculate_trust_score(
        fake_result["bot_percentage"],
        engagement_result["engagement_score"],
        image_risk=image_risk,
        image_band=image_band,
        image_confidence=image_conf,
    )

    return {
        "username": profile["username"],
        "full_name": profile["full_name"],
        "is_verified": profile["is_verified"],
        "raw_profile_data": profile,
        "engagement_data": engagement_data,
        "fake_follower_analysis": fake_result,
        "engagement_analysis": engagement_result,
        "comment_authenticity": comment_authenticity,
        "credential_analysis": credential_result,
        "image_analysis": image_result,
        "trust_score": trust_result
    }


    #hdhhhdshj