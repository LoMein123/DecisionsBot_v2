import torch
from torch import nn
from transformers import BertTokenizer, BertModel
import pandas as pd
from spellchecker import SpellChecker

from data import PROGRAMS

"""
Program Classifier Set-up
"""
# Encode programs as numbers and dictionarys to convert between them
label2num = {label: num for num, label in enumerate(sorted(PROGRAMS))}
num2label = {num: label for label, num in label2num.items()}

# Hyperparameters
bert_model_name = 'bert-base-uncased'
num_classes = len(label2num)
max_length = 128

# Tokenizer
tokenizer = BertTokenizer.from_pretrained(bert_model_name)

# Classifier architecture
class BERTClassifier(nn.Module):
    def __init__(self, bert_model_name, num_classes):
        super(BERTClassifier, self).__init__()
        self.bert = BertModel.from_pretrained(bert_model_name)          # BERT "layer"
        self.dropout = nn.Dropout(0.1)                                  # 10% Dropout Layer
        self.fc = nn.Linear(self.bert.config.hidden_size, num_classes)  # Fully Connected layer for dimension reduction of BERT outputs to num_classes

    def forward(self, input_ids, attention_mask):
        bert_outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = bert_outputs.pooler_output  # Get hidden state (i.e value) of the [CLS] token
        x = self.dropout(pooled_output)
        logits = self.fc(x)
        return logits

# Instantiate model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = BERTClassifier(bert_model_name, num_classes).to(device)

# Load weights
model.load_state_dict(torch.load("bert_program_classifier.pth"), True)

# Initialize the spell checker with the custom dictionary
spellcheck = SpellChecker()
spellcheck.word_frequency.load_text_file('corpus.txt')


"""
Function that checks and correct spelling
"""
def correct_spelling(text):
    corrected_text = []

    for word in text.split():
        if word in spellcheck:
            corrected_text.append(word)
        else:
            corrected_text.append(spellcheck.correction(word))

    # Fix NoneType errors (idk why this even happens)
    for index, word in enumerate(corrected_text):
        if word is None:
            corrected_text[index] = text.split()[index]

    return ' '.join(corrected_text)


"""
Function that predicts a program (i.e inputs a given program into the model), also returns confidence level
"""
def classify_program(program):
    model.eval()    # Enable evaluation mode

    encoding = tokenizer(program, return_tensors='pt', max_length=max_length, padding='max_length', truncation=True)    # Tokenize
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    with torch.no_grad():   # Disable gradient calculation
        logits = model(input_ids=input_ids, attention_mask=attention_mask)

        # Get predicted class
        preds = torch.argmax(logits, dim=1)
        predicted_program = num2label[preds.item()]

        # Calculate confidence
        outputs = torch.softmax(logits, dim = 1)
        confidence = torch.max(outputs, dim=1)[0].item()*100
        
    return predicted_program, confidence