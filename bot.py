import json
import logging
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.error import BadRequest

# লগিং সেটআপ করুন
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# আপনার ব্যক্তিগত টোকেন এবং আইডি এখানে দিন।
# এই মানগুলো সরাসরি কোডে না দিয়ে Render-এর এনভায়রনমেন্ট ভেরিয়েবল হিসেবে ব্যবহার করা নিরাপদ।
# তবে আপনার সুবিধার জন্য এখানে সরাসরি দেওয়া হলো।
BOT_TOKEN = "7845699149:AAEEKpzHFt5gd6LbApfXSsE8de64f8IaGx0"
ADMIN_CHANNEL_ID = -1002944346537  # টপ-আপ রিকোয়েস্টের জন্য
PUBLIC_CHANNEL_ID = -1003036699455  # পাবলিক আপডেটের জন্য

# --- ডাটাবেস হ্যান্ডলার ---
def load_data(file_name):
    """JSON ফাইল থেকে ডেটা লোড করে।"""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(data, file_name):
    """ডেটা JSON ফাইলে সংরক্ষণ করে।"""
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- কমান্ড হ্যান্ডলার ---
def start(update: Update, context: CallbackContext) -> None:
    """বট শুরু হলে এই কমান্ডটি কাজ করে।"""
    update.message.reply_text('স্বাগতম! আমি আপনার ইউজার এজেন্ট বট। /help লিখে কমান্ডগুলো দেখতে পারেন।')

def help_command(update: Update, context: CallbackContext) -> None:
    """সহায়তা কমান্ড।"""
    update.message.reply_text(
        """
        কমান্ডসমূহ:
        /mybalance - আপনার বর্তমান ব্যালেন্স দেখুন।
        /topup [টাকা] [ট্রানজ্যাকশন_আইডি] - ব্যালেন্স টপ আপ করার জন্য।
        /buyua - ইউজার এজেন্ট কিনুন।
        /rules - বটের নিয়মাবলী দেখুন।
        """
    )

def rules_command(update: Update, context: CallbackContext) -> None:
    """নিয়মাবলী দেখানোর জন্য কমান্ড।"""
    update.message.reply_text(
        """
        বট ব্যবহারের নিয়মাবলী:
        - কোনো ভুল ট্রানজ্যাকশন আইডি দিলে টপ আপ হবে না।
        - একবার কেনা ইউজার এজেন্ট আর ফেরত নেওয়া হবে না।
        - সকল প্রকার সমস্যা সমাধানের জন্য সাপোর্ট টিমের সাথে যোগাযোগ করুন।
        """
    )

# --- ব্যালেন্স এবং টপ-আপ ---
def my_balance(update: Update, context: CallbackContext) -> None:
    """ব্যবহারকারীর ব্যালেন্স দেখায়।"""
    user_id = str(update.effective_user.id)
    user_data = load_data('user_data.json')
    balance = user_data.get(user_id, {}).get('balance', 0)
    update.message.reply_text(f"আপনার বর্তমান ব্যালেন্স: ${balance:.2f}")

def top_up(update: Update, context: CallbackContext) -> None:
    """টপ-আপ রিকোয়েস্ট পাঠায়।"""
    try:
        if len(context.args) < 2:
            update.message.reply_text("ব্যবহারের নিয়ম: /topup [টাকার পরিমাণ] [ট্রানজ্যাকশন আইডি]")
            return
        
        amount = float(context.args[0])
        transaction_id = " ".join(context.args[1:])
        user = update.effective_user
        
        message = (
            f"💰 **নতুন টপ-আপ রিকোয়েস্ট!**\n\n"
            f"**ইউজার আইডি:** `{user.id}`\n"
            f"**ইউজারনেম:** @{user.username or 'N/A'}\n"
            f"**পরিমাণ:** ${amount:.2f}\n"
            f"**ট্রানজ্যাকশন আইডি:** `{transaction_id}`\n\n"
            "আপনি কি এই রিকোয়েস্টটি গ্রহণ করতে চান?"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ একসেপ্ট", callback_data=f'accept_{user.id}_{amount}'),
             InlineKeyboardButton("❌ রিজেক্ট", callback_data=f'reject_{user.id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        update.message.reply_text("আপনার টপ-আপ রিকোয়েস্টটি পাঠানো হয়েছে। দয়া করে অ্যাডমিনের অনুমোদনের জন্য অপেক্ষা করুন।")

    except ValueError:
        update.message.reply_text("টাকার পরিমাণটি ভুল। দয়া করে একটি সংখ্যা দিন।")
    except Exception as e:
        update.message.reply_text(f"একটি সমস্যা হয়েছে: {e}")

# --- ইউজার এজেন্ট লোড এবং সরবরাহ ---
def buy_user_agent(update: Update, context: CallbackContext) -> None:
    """ইউজার এজেন্ট বিক্রি করে।"""
    price = 10  # একটি ইউজার এজেন্টের দাম
    user_id = str(update.effective_user.id)
    user_data = load_data('user_data.json')
    
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0}

    current_balance = user_data[user_id].get('balance', 0)

    if current_balance < price:
        update.message.reply_text(f"দুঃখিত, আপনার ব্যালেন্স যথেষ্ট নয়। একটি ইউজার এজেন্টের দাম ${price}। আপনার বর্তমান ব্যালেন্স: ${current_balance:.2f}।")
        return

    ua_data = load_data('user_agents.json')
    available_uas = [ua for ua in ua_data if ua.get('status') == 'available']

    if not available_uas:
        update.message.reply_text("দুঃখিত, বর্তমানে কোনো ইউজার এজেন্ট নেই। নতুন স্টকের জন্য অপেক্ষা করুন।")
        return
        
    ua_to_sell = available_uas[0]
    
    # ব্যালেন্স আপডেট করুন
    user_data[user_id]['balance'] -= price
    save_data(user_data, 'user_data.json')
    
    # ইউজার এজেন্ট স্ট্যাটাস আপডেট করুন
    for ua in ua_data:
        if ua.get('id') == ua_to_sell.get('id'):
            ua['status'] = 'sold'
            break
    save_data(ua_data, 'user_agents.json')

    update.message.reply_text(f"আপনার ইউজার এজেন্টটি:\n\n`{ua_to_sell['user_agent']}`\n\n"
                              f"আপনার নতুন ব্যালেন্স: ${user_data[user_id]['balance']:.2f}")
    
    try:
        context.bot.send_message(
            chat_id=PUBLIC_CHANNEL_ID,
            text=f"🥳 একজন ব্যবহারকারী সফলভাবে একটি ইউজার এজেন্ট কিনেছেন! নতুন স্টক আসছে..."
        )
    except BadRequest:
        logging.error("পাবলিক চ্যানেলে মেসেজ পাঠাতে সমস্যা হয়েছে। নিশ্চিত করুন যে বটটি চ্যানেলের অ্যাডমিন এবং মেসেজ পাঠানোর অনুমতি আছে।")

# --- অ্যাডমিন বাটন হ্যান্ডলার ---
def button_callback(update: Update, context: CallbackContext) -> None:
    """অ্যাডমিন চ্যানেলের বাটনগুলো পরিচালনা করে।"""
    query = update.callback_query
    query.answer()
    
    data = query.data.split('_')
    action = data[0]
    user_id = data[1]

    user_data = load_data('user_data.json')

    if action == 'accept':
        amount = float(data[2])
        
        if user_id not in user_data:
            user_data[user_id] = {"balance": 0}
        
        user_data[user_id]['balance'] += amount
        save_data(user_data, 'user_data.json')
        
        try:
            # ব্যবহারকারীকে নোটিফিকেশন পাঠান
            context.bot.send_message(
                chat_id=user_id,
                text=f"✅ আপনার টপ-আপ সফল হয়েছে! আপনার অ্যাকাউন্টে ${amount:.2f} যোগ করা হয়েছে।"
            )
            query.edit_message_text(f"এই রিকোয়েস্টটি গ্রহণ করা হয়েছে।")
        except BadRequest:
            query.edit_message_text("ব্যবহারকারীকে মেসেজ পাঠানো যায়নি।")
            logging.error(f"ইউজার ID {user_id} কে মেসেজ পাঠানো যায়নি।")

    elif action == 'reject':
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=f"❌ দুঃখিত, আপনার টপ-আপ রিকোয়েস্টটি বাতিল করা হয়েছে। কোনো সমস্যা হলে সাপোর্টে যোগাযোগ করুন।"
            )
            query.edit_message_text(f"এই রিকোয়েস্টটি বাতিল করা হয়েছে।")
        except BadRequest:
            query.edit_message_text("ব্যবহারকারীকে মেসেজ পাঠানো যায়নি।")
            logging.error(f"ইউজার ID {user_id} কে মেসেজ পাঠানো যায়নি।")

# --- প্রধান ফাংশন ---
def main() -> None:
    """বটের প্রধান প্রবেশ বিন্দু।"""
    #Updater অবজেক্টটি BOT_TOKEN ব্যবহার করে তৈরি করা হয়েছে।
    #আগের ত্রুটিপূর্ণ কোডে থাকা 'update_queue' আর্গুমেন্টটি এখানে নেই।
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # কমান্ড হ্যান্ডলার যুক্ত করুন
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("rules", rules_command))
    dispatcher.add_handler(CommandHandler("mybalance", my_balance))
    dispatcher.add_handler(CommandHandler("topup", top_up))
    dispatcher.add_handler(CommandHandler("buyua", buy_user_agent))
    
    # বাটন হ্যান্ডলার যুক্ত করুন
    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    # পোলিং শুরু করুন
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
