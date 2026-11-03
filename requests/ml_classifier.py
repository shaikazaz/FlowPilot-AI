from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

training_texts = [
    "Need password reset",
    "Update employee profile",
    "Application server is down",
    "Urgent payment failure",
    "Request office stationery",
    "Customer cannot log in",
    "System outage affecting everyone",
    "Need new employee ID card",
    "Database is unavailable",
]

training_labels = [
    "Low",
    "Low",
    "High",
    "High",
    "Low",
    "Medium",
    "High",
    "Low",
    "High",
]

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(training_texts)

model = LogisticRegression(max_iter=1000)
model.fit(X, training_labels)

def predict_priority(text):
    text_features = vectorizer.transform([text])
    prediction = model.predict(text_features)
    return prediction[0]

def predict_category(text):
    text = text.lower()

    hr_keywords = [
        "employee", "leave", "payroll", "salary",
        "recruitment", "attendance", "hr", "holiday",
        "human resources", "onboarding"
    ]

    it_keywords = [
        "server", "database", "network", "software",
        "application", "system", "login", "password",
        "computer", "internet", "api", "technical",
        "bug", "error", "outage", "website"
    ]

    if any(word in text for word in hr_keywords):
        return "HR"

    if any(word in text for word in it_keywords):
        return "IT"

    return "General"


if __name__ == "__main__":
    test_request = "The entire application server is down"
    result = predict_priority(test_request)
    print("Request:", test_request)
    print("Predicted priority:", result)