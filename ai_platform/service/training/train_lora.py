import os

from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments


def main():
    # Configuration
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    output_dir = "./outputs/lora_run"
    dataset_path = "./training/datasets/train.jsonl"

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load tokenizer and model
    print(f"Loading tokenizer from {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading model from {model_name}...")
    model = AutoModelForCausalLM.from_pretrained(model_name)

    # Configure LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load and tokenize dataset
    print(f"Loading dataset from {dataset_path}...")
    dataset = load_dataset("json", data_files={"train": dataset_path})

    def tokenize_function(example):
        text = example["prompt"] + "\n" + example["response"]
        tokenized = tokenizer(text, truncation=True, max_length=1024, padding="max_length")
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    tokenized_datasets = dataset["train"].map(tokenize_function, batched=True)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        num_train_epochs=2,
        learning_rate=2e-4,
        logging_steps=10,
        save_steps=100,
        fp16=True,
        save_total_limit=3,
    )

    # Trainer
    trainer = Trainer(model=model, args=training_args, train_dataset=tokenized_datasets)

    # Train
    print("Starting training...")
    trainer.train()

    # Save
    print(f"Saving adapter to {output_dir}/lora_adapter...")
    model.save_pretrained(f"{output_dir}/lora_adapter")

    print("Training complete!")


if __name__ == "__main__":
    main()
