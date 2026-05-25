from src.database import SyncDatabase

if __name__ == "__main__":
    db = SyncDatabase()
    
    print("Deleting all products...")
    products_deleted = db.delete_all_products()
    print(f"Deleted {products_deleted} products")
    
    print("Deleting all price history...")
    history_deleted = db.delete_all_price_history()
    print(f"Deleted {history_deleted} price history records")
    
    print("Database reset complete!")