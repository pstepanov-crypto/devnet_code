import logging
import os
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
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

# Predefined options for some fields
field_options = {
    "side_a_type (dcim.interface, dcim.frontport, dcim.rearport)": ["dcim.interface", "dcim.frontport", "dcim.rearport"],
    "side_b_type (dcim.interface, dcim.frontport, dcim.rearport)": ["dcim.interface", "dcim.frontport", "dcim.rearport"]
}

# Define the start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    stop_event.clear()  # Clear the stop event to start the loop again

    # Initialize user-specific data
    user_data[user_id] = {
        'data': {},
        'current_field_index': 0
    }

    await ask_for_field(update, context, user_id)

# Function to ask for the current field
async def ask_for_field(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    current_field = expected_fields[user_data[user_id]['current_field_index']]

    if current_field in field_options:
        # Create inline keyboard buttons for predefined options
        keyboard = [
            [InlineKeyboardButton(option, callback_data=option)]
            for option in field_options[current_field]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Please select {current_field}:", reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Please enter {current_field}:")

# Define the callback query handler for inline buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    current_field = expected_fields[user_data[user_id]['current_field_index']]

    # Store the selected option
    user_data[user_id]['data'][current_field] = query.data

    # Move to the next field
    user_data[user_id]['current_field_index'] += 1

    if user_data[user_id]['current_field_index'] < len(expected_fields):
        await ask_for_field(update, context, user_id)
    else:
        # Save the collected data to CSV
        await form_csv(update, context)
        
        # Reset the data for the next iteration
        user_data[user_id] = {
            'data': {},
            'current_field_index': 0
        }

        # Ask for the first field again
        await query.message.reply_text("Thank you! Starting a new form.")
        await ask_for_field(update, context, user_id)

    await query.answer()

# Define the handle_message function
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if all fields have been collected
    if user_data[user_id]['current_field_index'] >= len(expected_fields):
        # Save the collected data to CSV
        await form_csv(update, context)
        
        # Reset the data for the next iteration
        user_data[user_id] = {
            'data': {},
            'current_field_index': 0
        }

        # Ask for the first field again
        await update.message.reply_text("Thank you! Starting a new form.")
        await ask_for_field(update, context, user_id)
        return

    # Extract the current expected field
    current_field = expected_fields[user_data[user_id]['current_field_index']]

    # Store the received data in the user-specific dictionary
    user_data[user_id]['data'][current_field] = update.message.text

    # Move to the next field
    user_data[user_id]['current_field_index'] += 1
    if user_data[user_id]['current_field_index'] < len(expected_fields):
        await ask_for_field(update, context, user_id)
    else:
        # Save the collected data to CSV
        await form_csv(update, context)
        
        # Reset the data for the next iteration
        user_data[user_id] = {
            'data': {},
            'current_field_index': 0
        }

        # Ask for the first field again
        await update.message.reply_text("Thank you! Starting a new form.")
        await ask_for_field(update, context, user_id)

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

# Main function to set up the application and handlers
def main():
    application = Application.builder().token(TOKEN).build()

    # Set up handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CommandHandler('form_csv', form_csv))
    application.add_handler(CommandHandler('clear', clear_csv))
    application.add_handler(CommandHandler('stop', stop))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
