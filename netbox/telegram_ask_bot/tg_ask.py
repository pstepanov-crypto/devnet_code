import logging
import os
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from threading import Event
import asyncio

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Your bot token from BotFather
TOKEN = ""

# Initialize the stop event for controlling the cyclic loop
stop_event = Event()

# Dictionary to store user-specific data
user_data = {}

# List of expected fields for the form
expected_fields = ["side_a_device", "side_a_name", "side_a_type (dcim.interface, dcim.frontport, dcim.rearport)", "label", "side_b_device", "side_b_name", "side_b_type (dcim.interface, dcim.frontport, dcim.rearport)"]

# Define the start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    stop_event.clear()  # Clear the stop event to start the loop again

    # Initialize user-specific data
    user_data[user_id] = {
        'data': {},
        'current_field_index': 0
    }

    await update.message.reply_text(f"Please tell me {expected_fields[user_data[user_id]['current_field_index']]}:")

# Define the handle_message function
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if all fields have been collected
    if user_data[user_id]['current_field_index'] >= len(expected_fields):
        await update.message.reply_text("Thank you! I have already collected all the information or type /start to continue.")
        return

    # Extract the current expected field
    current_field = expected_fields[user_data[user_id]['current_field_index']]

    # Store the received data in the user-specific dictionary
    user_data[user_id]['data'][current_field] = update.message.text

    # Move to the next field or finish if all fields are collected
    user_data[user_id]['current_field_index'] += 1
    if user_data[user_id]['current_field_index'] < len(expected_fields):
        await update.message.reply_text(f"Please tell me {expected_fields[user_data[user_id]['current_field_index']]}:")
    else:
        # Reset the index for the next interaction
        user_data[user_id]['current_field_index'] = 0
        await update.message.reply_text("Thank you! I have collected all the information. Type /form_csv to generate the CSV file.")

# Define the form_csv command
async def form_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if there is user-specific data to process
    if not user_data.get(user_id) or not user_data[user_id]['data']:
        await update.message.reply_text("No data to process. Please start a new form with /start.")
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
    await context.bot.send_document(chat_id=update.effective_chat.id, document=open("output.csv", "rb"))

    # Reset user-specific data for the next interaction
    user_data[user_id] = {
        'data': {},
        'current_field_index': 0
    }

# Define the clear_csv command
async def clear_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        os.remove("output.csv")
        await update.message.reply_text("The 'output.csv' file has been cleared.")
    except FileNotFoundError:
        await update.message.reply_text("There is no 'output.csv' file to clear.")

# Define the stop command
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stop_event.set()  # Set the event to stop the loop
    await update.message.reply_text("Cyclic requests have been stopped. Type /start to begin again.")

# Cyclic request loop
async def cyclic_requests(context: ContextTypes.DEFAULT_TYPE) -> None:
    while not stop_event.is_set():
        # Your cyclic request logic goes here.
        await asyncio.sleep(5)  # Delay between requests

# Main function to set up the application and handlers
def main():
    application = Application.builder().token(TOKEN).build()

    # Set up handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler('form_csv', form_csv))
    application.add_handler(CommandHandler('clear', clear_csv))
    application.add_handler(CommandHandler('stop', stop))

    # Schedule the cyclic_requests task to run periodically with up to 10 parallel instances
    application.job_queue.run_repeating(cyclic_requests, interval=5, first=0, job_kwargs={'max_instances': 10})

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
