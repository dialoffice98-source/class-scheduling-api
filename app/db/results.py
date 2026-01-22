from app.db.mongo_async import results_col

async def get_result(**query):
    return await results_col.find_one(query)