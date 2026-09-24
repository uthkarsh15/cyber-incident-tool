"""
Scaffolding for fine-tuning DistilBERT for Attack Type and Severity classification.
Requires labeled dataset in ml/data/labeled_incidents.csv.
"""
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset

MODEL_NAME = "distilbert-base-uncased"
DATA_PATH = "ml/data/labeled_incidents.csv"
OUTPUT_DIR = "ml/models/incident_classifier"

def load_and_prepare_data():
    try:
        df = pd.read_csv(DATA_PATH)
        return Dataset.from_pandas(df)
    except FileNotFoundError:
        print(f"Labeled data not found at {DATA_PATH}. Run dataset_exporter.py and label it first.")
        return None

def train():
    dataset = load_and_prepare_data()
    if dataset is None:
        return
        
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True)
        
    tokenized_datasets = dataset.map(tokenize_function, batched=True)
    
    num_labels = 10 
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=num_labels)
    
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        num_train_epochs=3,
        weight_decay=0.01,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets, 
    )
    
    print("Starting training (mock)...")
    # trainer.train()
    # model.save_pretrained(OUTPUT_DIR)
    # tokenizer.save_pretrained(OUTPUT_DIR)
    print("Training script scaffolding complete.")

if __name__ == "__main__":
    train()
