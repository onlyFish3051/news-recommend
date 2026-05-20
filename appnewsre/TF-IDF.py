from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from appnewsre.models import News, User

# 新闻文档集合
documents = News.objects.values_list('newscotent', flat=True)

# 创建TfidfVectorizer对象
vectorizer = TfidfVectorizer()

# 假设的用户画像，八大类新闻的阅读比例
user_profile = {
    User.objects.first().all()
}
# 将文档集合转换为TF-IDF特征矩阵
tfidf_matrix = vectorizer.fit_transform(documents)

# 获取特征名（词）
feature_names = vectorizer.get_feature_names_out()

# 使用TfidfVectorizer将新闻文本转化为TF-IDF矩阵
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(documents)

# 假设我们要计算第一条新闻和用户兴趣爱好的余弦相似度
news_vector = X[0].toarray()  # 提取第一条新闻的TF-IDF向量
user_interest_vector = np.zeros(len(vectorizer.get_feature_names_out()))
for category, weight in user_profile.items():
    index = list(user_profile.keys()).index(category)  # 注意：这只是一个示例索引
    if index < len(user_interest_vector):  # 确保索引在向量范围内
        user_interest_vector[index] = weight
# 计算余弦相似度
cosine_sim = cosine_similarity(news_vector.reshape(1, -1), user_interest_vector.reshape(1, -1))
