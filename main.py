import praw
from praw.models.util import stream_generator
from praw.models import Message
import logging
from logging.handlers import TimedRotatingFileHandler
import re
import uuid
from urllib.parse import quote
import time
import threading
import os
import imgur
import esixhandler
import furaffinityhandler
import inkbunnyhandler

logger = None
# As it turns out, praw is NOT thread safe.
reddit_inbox = praw.Reddit('bot')
reddit_comments = praw.Reddit('bot')
reddit_timed = praw.Reddit('bot')
subreddit = reddit_comments.subreddit("furry_irl")

ESIX_REGEX = r"(e621\.net/post/show/\d+)"
UPDATED_ESIX_REGEX = r"(e621\.net/posts/\d+)"
FURAFFINITY_REGEX = r"(furaffinity\.net/view/\d+)"
INKBUNNY_REGEX = r"(inkbunny\.net/s/\d+)"

MAIL_START_MESSAGE = "OwO, what's this? You want me to mirror these links for you? Here you go!\n\n"
COMMENT_START_MESSAGE = "Hewwo, FAToFACDN here! I notice that you've linked images from e621/FurAffinity/Inkbunny without full quality direct links, I'm here to provide them!\n\n"
COMMENT_DETECTED_MESSAGE = "I also noticed that you tried to add a direct link, but linked a lower resolution one, Please look at [this guide](https://imgur.com/a/RpklH) to learn how to properly add direct links to your post!\n\n"
END_MESSAGE = "***\n^^Bot ^^Created ^^By ^^Hidoni, ^^Have ^^I ^^made ^^an ^^error? [^^Message ^^creator](https://www.reddit.com/message/compose/?to=Hidoni&subject=Bot%20Error) ^^| [^^Blacklist ^^yourself](https://www.reddit.com/message/compose/?to=FAToFacdn&subject=Blacklist&message=Hi,%20I%20want%20to%20be%20blacklisted) ^^| [^^How ^^to ^^properly ^^give ^^direct ^^links](https://imgur.com/a/RpklH) ^^| ^^Check ^^out ^^my ^^source ^^code ^^on ^^[GitHub](https://github.com/Hidoni/FAToFACDN)! ^^| ^^If ^^this ^^comment ^^goes ^^below ^^0 ^^karma, ^^It ^^will ^^be ^^deleted."

exit_flag = False


def setup_logging():
    file = TimedRotatingFileHandler("logs/FAToFACDN.log", when='midnight', encoding="utf-8")
    console = logging.StreamHandler()
    console.setLevel("INFO")
    logging.basicConfig(format="{asctime:s} {name:s}:{levelname:s} {message:s}", style='{', handlers=[file, console], level=logging.DEBUG)
    global logger
    logger = logging.getLogger("main")


def parse(content):
    content = content.lower()
    content = content.replace("e926.net", "e621.net")
    content = content.replace("full", "view")
    matches = re.findall(ESIX_REGEX, content)
    matches += re.findall(UPDATED_ESIX_REGEX, content)
    matches += re.findall(FURAFFINITY_REGEX, content)
    matches += re.findall(INKBUNNY_REGEX, content)
    return list(dict.fromkeys(matches))  # Remove duplicate matches


def convert(urls):
    info = []
    for url in urls:
        url = "https://www." + url.lower()
        try:
            if "e621" in url:
                info.append(esixhandler.get(url))
            elif "furaffinity" in url:
                info.append(furaffinityhandler.get(url))
            else:
                info.append(inkbunnyhandler.get(url))
        except Exception as e:
            logger.debug(f"Got Exception {e} when trying to add {url}")
            continue  # Ignore the one that's causing issues.
    return [post for post in info if post is not None]


def sort_tags(tags):
    replace_list = [["ambiguous_gender", "male", "female", "intersex", "andromorph", "gynomorph", "herm", "maleherm", "manly", "girly", "tomboy"], ["bondage", "domination", "submissive", "sadism", "masochism", "size_play", "hyper", "macro", "micro", "'pok\\xc3\\xa9mon'", "transformation", "cock_transformation", "gender_transformation", "post_transformation", "scat_transformation", "inflation", "belly_expansion", "cum_inflation", "scat_inflation", "vore", "soft_vore", "hard_vore", "absorption_vore", "soul_vore", "anal_vore", "auto_vore", "breast_vore", "nipple_vore", "cock_vore", "oral_vore", "tail_vore", "imminent_vore", "post_vore", "unbirthing", "cannibalism", "vore_sex", "scat", "watersports", "gore", "grotesque_death", "crush", "stomping", "snuff", "necrophilia", "ballbusting", "cock_and_ball_torture", "genital_mutilation", "rape", "abuse", "degradation", "forced", "gang_rape", "mind_break", "public_use", "questionable_consent", "assisted_rape", "oral_rape", "tentacle_rape", "armpit_fetish", "balloon_fetish", "fart_fetish", "foot_fetish", "hoof_fetish", "navel_fetish", "sock_fetish", "what", "why"], ["male/female", "male/male", "female/female", "intersex/male", "andromorph/male", "gynomorph/male", "herm/male", "maleherm/male", "intersex/female", "andromorph/female", "gynomorph/female", "herm/female", "maleherm/female", "intersex/intersex", "andromorph/andromorph", "gynomorph/andromorph", "gynomorph/gynomorph", "gynomorph/herm", "herm/andromorph", "herm/herm", "maleherm/andromorph", "maleherm/gynomorph", "maleherm/herm", "maleherm/maleherm", "ambiguous/ambiguous", "male/ambiguous", "female/ambiguous", "intersex/ambiguous", "andromorph/ambiguous", "gynomorph/ambiguous", "herm/ambiguous", "maleherm/ambiguous"], ["feral", "semi-anthro", "humanoid", "human", "taur"], ["penetration", "anal_penetration", "cloacal_penetration", "oral_penetration", "urethral_penetration", "vaginal_penetration", "cervical_penetration", "double_penetration", "double_anal", "double_vaginal", "triple_penetration", "triple_anal", "triple_vaginal", "oral", "cloacalingus", "cunnilingus", "collaborative_cunnilingus", "fellatio", "beakjob", "collaborative_fellatio", "deep_throat", "double_fellatio", "oral_knotting", "rimming", "deep_rimming", "snout_fuck", "sideways_oral", "tonguejob", "licking", "ball_lick", "penis_lick", "oral_masturbation", "autocunnilingus", "autofellatio", "auto_penis_lick", "autorimming", "autotonguejob", "fisting", "anal_fisting", "double_fisting", "urethral_fisting", "vaginal_fisting", "fingering", "anal_fingering", "clitoral_fingering", "cloacal_fingering", "vaginal_fingering", "urethral_fingering", "fingering_self", "fingering_partner", "frottage", "grinding", "hot dogging", "tailjob", "titfuck", "tribadism"], ["69_position", "amazon_position", "anvil_position", "arch_position", "chair_position", "cowgirl_position", "deck_chair_position", "from_behind_position", "leg_glider_position", "lotus_position", "mastery_position", "missionary_position", "piledriver_position", "prison_guard_position", "reverse_cowgirl_position", "reverse_piledriver_position", "reverse_missionary_position", "sandwich_position", "speed_bump_position", "spoon_position", "stand_and_carry_position", "t_square_position", "table_lotus_position", "totem_pole_position", "train_position", "triangle_position", "unusual_position", "wheelbarrow_position", "1691_position", "ass_to_ass", "daisy_chain", "doggystyle", "mating_press", "mounting", "polesitting", "reverse_spitroast", "spitroast"]]
    new_order = []
    for tag_list in replace_list:
        for tag in tags:
            if tag in tag_list:
                new_order.append(tag)
    for tag in tags:
            if tag not in new_order:
                new_order.append(tag)
    return new_order


def format_tags(tags):
    omitted = len(tags) - 30
    formatted = []
    tags = tags[:30]
    for tag in tags:
        formatted.append(''.join([x if x not in ['*', '~', '_', '^', '\\', '(', ')', '[', ']', '>'] else '\\' + x for x in tag]))
    return "^" + ' ^'.join(formatted) + f'{f" ^and ^{omitted} ^Omitted ^Tags" if omitted > 0 else ""}'


def upload_and_format(post, path):
    if isinstance(post.direct_link, list):
        file_names = post.download(path)
        return ' | '.join([f'[Link {x + 1}]({post.direct_link[x]})' for x in range(len(post.direct_link))]) + f" | Title: {post.image_name} | Artist/Uploader: {', '.join(post.artist)} | Rating: {post.rating} | [Imgur Mirror]({imgur.mirror(file_names, post.image_name)}) \n\n^Tags: {format_tags(sort_tags(post.tags)) if post.tags else '^None!'}\n\n"
    file_name = post.download(path)
    return f"[Link]({post.direct_link}) | Title: {post.image_name} | Artist/Uploader: {', '.join(post.artist)} | Rating: {post.rating} | [Imgur Mirror]({imgur.mirror(file_name, post.image_name)}) \n\n^Tags: {format_tags(sort_tags(post.tags)) if len(post.tags) > 0 else '^None!'}\n\n"


def handle_inbox():
    global exit_flag
    while True:
        try:
            for mail in stream_generator(reddit_inbox.inbox.unread):
                if exit_flag:
                    exit(-1)
                if isinstance(mail, Message):
                    if mail.subject.lower() == "blacklist":
                        logger.info(f"Found a blacklist request from {mail.author.name}")
                        with open("blacklist", 'a') as f:
                            f.write(mail.author.name + "\n")
                            logger.debug(f"Added {mail.author.name} to the blacklist.")
                    else:  # Potentially someone wanting to mirror via DMs
                        urls = parse(mail.body)
                        if urls:
                            logger.info(f"Got PM Mirror Request from {mail.author.name}")
                            logger.debug(f"Found the following URLs in DM Request: {urls}")
                            posts = convert(urls)
                            if posts:
                                response = MAIL_START_MESSAGE
                                for post in posts:
                                    try:
                                        response += upload_and_format(post, f"images/{uuid.uuid4().hex}")
                                    except Exception:
                                        continue
                                response += END_MESSAGE
                                if response != MAIL_START_MESSAGE + END_MESSAGE:
                                    mail.reply(response)
                            logger.info(f"Replied to {mail.author.name}'s DM request.")
                        else:
                            logger.debug(f"Got PM From {mail.author.name}, but it's irrelevant")
                mail.mark_read()
        except:
            pass


def can_reply(comment):
    return not (comment.author.name + "\n" in open("blacklist", 'r').read() or comment.id + "\n" in open("replies", 'r'))


def source_exists(link, original):
    original = original.lower().replace("e926.net", "e621.net").replace("full", "view")
    return (quote(link, safe="://") in quote(original, safe="://")) or (quote(link, safe="://") in original) or (link in original)  # Just to be safe...


def handle_comments():
    for comment in subreddit.stream.comments():
        logger.info(f"Checking comment with ID: {comment.id}, By: {comment.author.name}")
        logger.debug(f"Comment contents are: {comment.body}\nLink is: https://www.reddit.com{comment.permalink}?context=5")
        if can_reply(comment):
            urls = parse(comment.body)
            if urls:
                logger.debug(f"Found the following URLs in comment: {urls}")
                posts = convert(urls)
                response = COMMENT_START_MESSAGE
                sample_found = False
                for post in posts[:]:  # Need to iterate over a copy of the list otherwise list.remove isn't happy.
                    if post.sample_url is not None and not sample_found:
                        if source_exists(post.sample_url[8:], comment.body):
                            response += COMMENT_DETECTED_MESSAGE
                            sample_found = True
                    if isinstance(post.direct_link, list):
                        for link in post.direct_link[:]:
                            if source_exists(link, comment.body):
                                post.direct_link.remove(link)
                        if not post.direct_link:
                            posts.remove(post)
                    else:
                        if source_exists(post.direct_link, comment.body):
                            posts.remove(post)
                for post in posts:
                    response += upload_and_format(post, f"images/{uuid.uuid4().hex}")
                response += END_MESSAGE
                if response != COMMENT_START_MESSAGE + END_MESSAGE and response != COMMENT_START_MESSAGE + COMMENT_DETECTED_MESSAGE + END_MESSAGE:
                    with open("replies", 'a') as f:
                        f.write(f"{comment.id}\n")
                    comment.reply(response)
                    logger.info(f"Replied to message with ID: {comment.id}")
                    logger.debug(f"Reply was:{response}")
            else:
                logger.debug("Could not find any valid URLs in comment.")


def handle_timed_actions():
    global exit_flag
    while True:
        if exit_flag:
            exit(-1)
        logger.info("Deleting comments which are under a score of 0 and old images.")
        comments = filter(lambda comment: comment.score < 0, sorted(reddit_timed.user.me().comments.new(limit=None), key=lambda comment: comment.score))
        for comment in comments:
            logger.debug(f"Deleting comment with a score of {comment.score}\nComment contents are: {comment.body}\nLink is: https://www.reddit.com{comment.permalink}?context=5")
            comment.delete()
        for filename in os.listdir(f"{os.getcwd()}/images/"):
            if filename[-4:] in ['.png', '.jpg', '.gif', '.bmp'] or filename[-5:] in ['.webm']:
                logger.debug(f"Deleting file: {filename}")
                try:
                    os.remove(f"images/{filename}")
                except:
                    pass
        time.sleep(3600)  # Once an hour, check last 1000 comments for any below a threshold of 0


if __name__ == '__main__':
    setup_logging()
    inbox_thread = threading.Thread(target=handle_inbox)
    timed_thread = threading.Thread(target=handle_timed_actions)
    inbox_thread.start()
    timed_thread.start()
    while True:
        try:
            handle_comments()
        except:
            pass
    exit_flag = True
    exit(-1)  # If we get to this point, we should exit with a bad exit code.
