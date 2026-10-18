# Required C3 video: actual recording sequence

This is a recording script, not a video or a claim that recording occurred. Use only fictional contact details.

1. Show the business PDF/summary and the separate persona/instructions blocks. Briefly identify the three router paths.
2. Run `python live_check.py` with a configured key. Preserve failures if they occur; do not substitute scripted fixtures.
3. Run `python app.py`. Ask “Which beginner workshops do you offer?” Show the grounded answer.
4. Say “I am interested in AI Foundations. Please contact me.” Let the assistant request missing fields. Reply with “My name is Dana Saleh. My email is dana@example.com. My note is: Interested in AI Foundations.”
5. Show the resulting native tool call, successful receipt, and exact lead JSONL fields. Explain that this is a lead, not a booking.
6. Send “Feedback: Please add evening sessions.” Show `record_feedback` and its record.
7. Ask “Is VAT included in tuition?” Show uncertainty and the model-called feedback tool, rather than an invented tax answer.
8. Send “Do not log this. What is your accreditation?” Show that no new feedback record or persistent trace is written for that turn.
9. Open one reflection trace and show both draft and revision. An unchanged draft is legitimate; do not manufacture a correction.
10. Show local verification results, state the test scope, and add the video file or accessible video link to the GitHub repository. Add the actual repository URL in the course submission.

Suggested length: 3-5 minutes; this is a suggestion because C3 gives no video-length requirement.
