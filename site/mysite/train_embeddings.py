import os
import pandas as pd
import torch
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, InputExample, losses, models, evaluation
from utils.embeddings import create_job_text

# Configuration
TEACHER_MODEL_NAME = 'intfloat/multilingual-e5-base' # 768 dim, matches BERT base
STUDENT_MODEL_NAME = 'bert-base-multilingual-cased'
BATCH_SIZE = 16
EPOCHS = 3
OUTPUT_PATH = 'site/mysite/fine_tuned_bert'
DATA_PATH = 'model/jobs.csv'

def train():
    print(f"Loading data from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    
    # Prepare training texts
    train_texts = []
    print("Preparing training examples...")
    for _, row in df.iterrows():
        # Construct text exactly as the app does
        text = create_job_text(
            title=str(row.get('title', '')),
            knowledge=str(row.get('knoladge', '')), # Note: csv likely has 'knoladge' typo based on previous context
            city=str(row.get('city', '')),
            company=str(row.get('company', '')),
            additions=str(row.get('addition', ''))
        )
        if text.strip():
            train_texts.append(text)
            
    print(f"Collected {len(train_texts)} training examples.")
    
    # Initialize models
    print(f"Loading Teacher: {TEACHER_MODEL_NAME}...")
    teacher_model = SentenceTransformer(TEACHER_MODEL_NAME)
    
    print(f"Loading Student: {STUDENT_MODEL_NAME}...")
    # Use simple SentenceTransformer wrapper for Student too
    student_model = SentenceTransformer(STUDENT_MODEL_NAME)
    
    # Generate Teacher Embeddings (Targets)
    print("Generating teacher embeddings (this may take a while)...")
    # e5 requires "passage: " prefix
    teacher_inputs = [f"passage: {t}" for t in train_texts]
    with torch.no_grad():
        teacher_embeddings = teacher_model.encode(teacher_inputs, show_progress_bar=True, convert_to_numpy=True)
    
    # Create InputExamples for Distillation (text -> target_embedding)
    # We treat this as a regression task: Input is text, label is the float vector
    # SentenceTransformer doesn't have a direct "Distillation" reader, but we can use standard inputs
    # However, standard losses expect labels to be class ints or similarity floats, NOT full vectors.
    # We will implement a custom loop or use a dataset that returns (text, embedding) and custom loss.
    
    # Actually, simpler: Use PyTorch directly for the training loop over the student model
    # SentenceTransformer is just a nn.Module.
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on {device}...")
    student_model.to(device)
    student_model.train()
    
    # Create DataLoader
    class DistillationDataset(torch.utils.data.Dataset):
        def __init__(self, texts, targets):
            self.texts = texts
            self.targets = targets
            
        def __len__(self):
            return len(self.texts)
            
        def __getitem__(self, idx):
            return self.texts[idx], self.targets[idx]

    dataset = DistillationDataset(train_texts, teacher_embeddings)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    optimizer = torch.optim.AdamW(student_model.parameters(), lr=2e-5)
    loss_fn = torch.nn.MSELoss()
    
    for epoch in range(EPOCHS):
        total_loss = 0
        steps = 0
        for batch_texts, batch_targets in dataloader:
            optimizer.zero_grad()
            
            # Tokenize and compute student embeddings
            # Note: student does NOT use prefixes
            features = student_model.tokenize(batch_texts)
            for key in features:
                features[key] = features[key].to(device)
                
            student_output = student_model(features)['sentence_embedding']
            
            # Move targets
            targets = batch_targets.to(device)
            
            # MSE Loss
            loss = loss_fn(student_output, targets)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            steps += 1
            
            if steps % 10 == 0:
                print(f"Epoch {epoch+1}, Step {steps}, Loss: {loss.item():.4f}")
                
        avg_loss = total_loss / steps
        print(f"Epoch {epoch+1} Complete. Average Loss: {avg_loss:.4f}")
        
    print(f"Saving fine-tuned model to {OUTPUT_PATH}...")
    student_model.save(OUTPUT_PATH)
    print("Done!")

if __name__ == "__main__":
    train()
