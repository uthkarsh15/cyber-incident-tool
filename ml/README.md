# Machine Learning Integration

This directory contains the scaffolding for transitioning from our rule-based agents (Phase 5) to Machine Learning models.

## Workflow

1. **Collect Data**: Run `python dataset_exporter.py` to extract incidents parsed by our heuristic agents.
2. **Label Data**: Manually review and correct the heuristic labels (`attack_type`, `severity`).
3. **Train Classifier**: Once you have ~1000 labeled examples, run `python train_classifier.py` to fine-tune DistilBERT.
4. **Train NER**: Use `train_ner.py` guidelines to train a custom spaCy model for Indian threat actors.

## Agent Integration

Once models are trained and saved in `ml/models/`, update the agents in `backend/app/agents/`:

**In `classification_agent.py`:**
```python
from transformers import pipeline
classifier = pipeline("text-classification", model="../ml/models/incident_classifier")

# Replace keyword matching with model inference:
prediction = classifier(text)
data["attack_type"] = prediction[0]["label"]
```

**In `insight_agent.py`:**
```python
import spacy
# Replace default en_core_web_sm with custom trained model
self.nlp = spacy.load("../ml/models/custom_ner")
```
