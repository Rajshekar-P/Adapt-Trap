def get_summary_metrics(df):
    return {
        "count": len(df),
        "unique_ips": df["ip"].nunique(),
        "tagged": df["tags"].apply(lambda x: len(x) > 0).sum()
    }