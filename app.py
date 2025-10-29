from flask import Flask, render_template, request, jsonify
import pandas as pd

app = Flask(__name__)

# ---------- Load Data from Local Files ----------
job_details_df = pd.read_csv("job_details.csv")
skill_time_df = pd.read_csv("skills_completion_time.csv")
foundation_df = pd.read_csv("foundation_courses.csv")
professional_df = pd.read_csv("professional_courses.csv")

# ---------- Utility ----------
def parse_skills(skill_text):
    if not isinstance(skill_text, str) or not skill_text.strip():
        return []
    return [s.strip().lower() for s in skill_text.split(",")]

# ---------- Gap Analysis ----------
def find_missing_skills(target_job, current_skills):
    # Exact match first
    job_row = job_details_df[job_details_df["Job Title"].str.lower() == target_job.lower()]

    # Fallback: partial match
    if job_row.empty:
        job_row = job_details_df[job_details_df["Job Title"].str.lower().str.contains(target_job.lower(), na=False)]

    if job_row.empty:
        return None, None, None, None

    job_row = job_row.iloc[0]
    required_skills = parse_skills(job_row["Skill Requirements"])
    user_skills = parse_skills(current_skills)

    missing = [s for s in required_skills if s not in user_skills]
    matched = [s for s in required_skills if s in user_skills]

    return job_row["Job Title"], required_skills, matched, missing


def calculate_total_duration(missing_skills, hours_per_day=2):
    total_hours = 0
    skill_hours = {}

    for skill in missing_skills:
        row = skill_time_df[skill_time_df["Skill Name"].str.lower() == skill.lower()]
        if not row.empty:
            hours = row.iloc[0]["Estimated Completion Time (hours)"]
            skill_hours[skill] = hours
            total_hours += hours
        else:
            skill_hours[skill] = None

    total_days = total_hours / hours_per_day if hours_per_day > 0 else total_hours
    return round(total_days, 1), skill_hours


# ---------- Professional Course Recommendation ----------
def suggest_professional_courses(missing_skills, limit=4):
    if not missing_skills:
        return []

    filtered = professional_df[
        professional_df["skills"].str.lower().apply(
            lambda s: any(skill.lower() in s for skill in missing_skills)
        )
    ]

    updated_courses = []
    for _, course in filtered.iterrows():
        course_skill_set = set(parse_skills(course["skills"]))
        covered_skills = [s for s in missing_skills if s in course_skill_set]
        updated_courses.append({
            "title": course["title"],
            "link": course["link"],
            "provider": course["provider"],
            "platform": course["platform"],
            "credential": course["credential"],
            "duration": course["duration"],
            "covered_skills": covered_skills,
            "total_covered": len(covered_skills)
        })

    updated_courses.sort(key=lambda c: c["total_covered"], reverse=True)
    return updated_courses[:limit]


# ---------- Foundation Course Recommendation ----------
def suggest_foundation_courses(missing_skills, limit=4):
    if not missing_skills:
        return []

    filtered = foundation_df[
        foundation_df["skills"].str.lower().apply(
            lambda s: any(skill.lower() in s for skill in missing_skills)
        )
    ]

    updated_courses = []
    for _, course in filtered.iterrows():
        course_skill_set = set(parse_skills(course["skills"]))
        covered_skills = [s for s in missing_skills if s in course_skill_set]
        updated_courses.append({
            "title": course["title"],
            "link": course["link"],
            "provider": course["provider"],
            "platform": course["platform"],
            "credential": course["credential"],
            "duration": course["duration"],
            "rating": course["rating"],
            "covered_skills": covered_skills,
            "total_covered": len(covered_skills)
        })

    updated_courses.sort(key=lambda c: (c["total_covered"], c["rating"]), reverse=True)
    return updated_courses[:limit]


# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        target_job = request.form["target_job"]
        current_skills = request.form["current_skills"]
        hours_per_day = float(request.form.get("hours_per_day", 2))

        job_id, required, matched, missing = find_missing_skills(target_job, current_skills)
        if not required:
            return render_template("result.html", error="❌ Job not found in file database.")

        total_days, skill_hours = calculate_total_duration(missing, hours_per_day)
        professional_courses = suggest_professional_courses(missing)
        foundation_courses = suggest_foundation_courses(missing)

        return render_template(
            "result.html",
            target_job=target_job,
            required=required,
            matched=matched,
            missing=missing,
            total_days=total_days,
            skill_hours=skill_hours,
            hours_per_day=hours_per_day,
            professional_courses=professional_courses,
            foundation_courses=foundation_courses
        )

    return render_template("index.html")


# ---------- Job Search API ----------
@app.route("/search_jobs")
def search_jobs():
    query = request.args.get("q", "").lower()
    jobs = job_details_df[job_details_df["Job Title"].str.lower().str.contains(query, na=False)]["Job Title"].head(10).tolist()
    return jsonify(jobs)


if __name__ == "__main__":
    app.run(debug=True)
