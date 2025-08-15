def get_tag_insights(df):
    from collections import Counter
    all_tags = df["tags"].explode()
    return dict(Counter(all_tags))