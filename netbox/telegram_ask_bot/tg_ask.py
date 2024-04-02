import logging
import os
import pandas as pd
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters
from telegram import Update

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Your bot token from BotFather
TOKEN = "token_id"

# Initialize the updater and dispatcher
updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

# Dictionary to store user-specific data
user_data = {}

# List of expected fields for the form
expected_fields = ["side_a_device", "side_a_name", "side_a_type ( dcim.interface, dcim.frontport, dcim.rearport)", "label", "side_b_device", "side_b_name", "side_b_type ( dcim.interface, dcim.frontport, dcim.rearport)"]

# Define the start command
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # Initialize user-specific data
    user_data[user_id] = {
        'data': {},
        'current_field_index': 0
    }

    update.message.reply_text(f"Please tell me {expected_fields[user_data[user_id]['current_field_index']]}:")

# Define the handle_message function
def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # Check if all fields have been collected
    if user_data[user_id]['current_field_index'] >= len(expected_fields):
        update.message.reply_text("Thank you! I have already collected all the information or type /start to continue.")
        return

    # Extract the current expected field
    current_field = expected_fields[user_data[user_id]['current_field_index']]

    # Store the received data in the user-specific dictionary
    user_data[user_id]['data'][current_field] = update.message.text

    # Move to the next field or finish if all fields are collected
    user_data[user_id]['current_field_index'] += 1
    if user_data[user_id]['current_field_index'] < len(expected_fields):
        update.message.reply_text(f"Please tell me {expected_fields[user_data[user_id]['current_field_index']]}:")
    else:
        # Reset the index for the next interaction
        user_data[user_id]['current_field_index'] = 0
        update.message.reply_text("Thank you! I have collected all the information. Type /form_csv to generate the CSV file.")

# Define the form_csv command
def form_csv(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # Check if there is user-specific data to process
    if not user_data.get(user_id) or not user_data[user_id]['data']:
        update.message.reply_text("No data to process. Please start a new form with /start.")
        return

    # Create a DataFrame from the collected data
    new_data_df = pd.DataFrame(user_data[user_id]['data'], index=[0])

    # Load existing data from the CSV file if it exists
    try:
        existing_data_df = pd.read_csv("output.csv")
        # Concatenate the new data with the existing DataFrame
        combined_df = pd.concat([existing_data_df, new_data_df], ignore_index=True)
    except FileNotFoundError:
        # If the file doesn't exist, use only the new data
        combined_df = new_data_df

    # Save the updated DataFrame to the CSV file
    combined_df.to_csv("output.csv", index=False)

    # Send the CSV file to the user
    context.bot.send_document(chat_id=update.effective_chat.id, document=open("output.csv", "rb"))

    # Reset user-specific data for the next interaction
    user_data[user_id] = {
        'data': {},
        'current_field_index': 0
    }

# Define the clear_csv command
def clear_csv(update: Update, context: CallbackContext) -> None:
    try:
        os.remove("output.csv")
        update.message.reply_text("The 'output.csv' file has been cleared.")
    except FileNotFoundError:
        update.message.reply_text("There is no 'output.csv' file to clear.")

# Set up handlers
start_handler = CommandHandler('start', start)
message_handler = MessageHandler(Filters.text & ~Filters.command, handle_message)
form_csv_handler = CommandHandler('form_csv', form_csv)
clear_csv_handler = CommandHandler('clear', clear_csv)

# Add handlers to the dispatcher
dispatcher.add_handler(start_handler)
dispatcher.add_handler(message_handler)
dispatcher.add_handler(form_csv_handler)
dispatcher.add_handler(clear_csv_handler)

# Start the bot
updater.start_polling()
updater.idle()
