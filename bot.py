import discord
from discord.ext import commands, tasks
from logic import DatabaseManager, hide_img, create_collage
from config import TOKEN, DATABASE
import os
import cv2

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
manager = DatabaseManager(DATABASE)
manager.create_tables()

@bot.command()
async def start(ctx):
    user_id = ctx.author.id
    if user_id in manager.get_users():
        await ctx.send("Zaten kayıtlısınız!")
    else:
        manager.add_user(user_id, ctx.author.name)
        await ctx.send("Merhaba! Hoş geldiniz! Başarılı bir şekilde kaydoldunuz! Her dakika yeni resimler alacaksınız ve bunları elde etme şansınız olacak! Bunu yapmak için 'Al!' butonuna tıklamanız gerekiyor! Sadece 'Al!' butonuna tıklayan ilk üç kullanıcı resmi alacaktır! =)")

@bot.command()
async def get_my_score(ctx):
    user_id = ctx.author.id
    info = manager.get_winners_img(user_id)
    prizes = [x[0] for x in info]
    image_paths = os.listdir('img')
    image_paths = [f'img/{x}' if x in prizes else f'hidden_img/{x}' for x in image_paths]
    
    collage = create_collage(image_paths)
    collage_path = f'collage_{user_id}.jpg'
    cv2.imwrite(collage_path, collage)
    
    with open(collage_path, 'rb') as img:
        file = discord.File(img)
        await ctx.send(file=file, content="İşte ödül kolajınız!")
    os.remove(collage_path)  

@bot.command()
async def preview(ctx, prize_id):
    try:
        img = manager.get_prize_img(prize_id)
        hidden_img_path = f'hidden_img/{img}'
        with open(hidden_img_path, 'rb') as photo:
            file = discord.File(photo)
            await ctx.send(file=file, content="İşte bulanık önizleme!")
    except Exception as e:
        await ctx.send("Bir hata oluştu. Lütfen geçerli bir ödül kimliği girin.")

@tasks.loop(minutes=1)
async def send_message():
    for user_id in manager.get_users():
        prize_id, img = manager.get_random_prize()[:2]
        hide_img(img)
        user = await bot.fetch_user(user_id)
        if user:
            await send_image(user, f'hidden_img/{img}', prize_id)
        manager.mark_prize_used(prize_id)

async def send_image(user, image_path, prize_id):
    with open(image_path, 'rb') as img:
        file = discord.File(img)
        button = discord.ui.Button(label="Al!", custom_id=str(prize_id))
        view = discord.ui.View()
        view.add_item(button)
        await user.send(file=file, view=view)

@bot.command()
async def rating(ctx):
    res = manager.get_rating()
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res
    await ctx.send(f"```\n{res}\n```")

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data['custom_id']
        user_id = interaction.user.id

        if manager.get_winners_count(custom_id) < 3:
            res = manager.add_winner(user_id, custom_id)
            if res:
                img = manager.get_prize_img(custom_id)
                with open(f'img/{img}', 'rb') as photo:
                    file = discord.File(photo)
                    await interaction.response.send_message(file=file, content="Tebrikler, resmi aldınız!")
            else:
                await interaction.response.send_message(content="Bu resme zaten sahipsiniz!", ephemeral=True)
        else:
            await interaction.response.send_message(content="Maalesef, birisi bu resmi çoktan aldı...", ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')
    if not send_message.is_running():
        send_message.start()

bot.run(TOKEN)