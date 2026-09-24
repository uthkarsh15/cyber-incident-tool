import os
import pandas as pd
import asyncio
from sqlalchemy import select
from backend.app.database import async_session
from backend.app.models.incident import Incident

async def export_data(output_path="ml/data/raw_incidents.csv"):
    """Exports incidents from PostgreSQL into a CSV for manual labeling or training."""
    async with async_session() as session:
        result = await session.execute(select(Incident))
        incidents = result.scalars().all()
        
    data = []
    for inc in incidents:
        data.append({
            "id": inc.id,
            "title": inc.title,
            "description": inc.description,
            "content": inc.raw_content,
            "attack_type_label": inc.attack_type, 
            "severity_label": inc.severity,
            "sector_label": inc.sector_id
        })
        
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} records to {output_path}")

if __name__ == "__main__":
    asyncio.run(export_data())
