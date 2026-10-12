import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1. Load dataset
df = pd.read_excel("amazon-products2.xlsx")
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Handle missing text values by filling with empty strings
df['gift_text'] = df['gift_text'].fillna('')

# 2. Initialize TF-IDF Vectorizer
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(df['gift_text'])

def recommend_gifts(user_query, top_n=6):
    # Transform user query into vector
    query_vector = vectorizer.transform([user_query])
    
    # Calculate cosine similarity between query and all products
    similarity_scores = cosine_similarity(query_vector, tfidf_matrix).flatten()
    
    # Get top matching indices
    top_indices = similarity_scores.argsort()[::-1][:top_n]
    
    # Build results dataframe
    results = df.iloc[top_indices].copy()
    results['similarity_score'] = similarity_scores[top_indices]
    
    return results[['title', 'brand', 'final_price', 'similarity_score']]

# Test query
test_query = "birthday gift for my brother who loves running"
print(f"Testing recommendations for query: '{test_query}'\n")
print(recommend_gifts(test_query))