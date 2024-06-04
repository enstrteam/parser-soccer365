from playwright.sync_api import Playwright, sync_playwright
from time import sleep
from datetime import datetime 
import csv




def get_status(game):
    status = game.query_selector('.status').inner_text()

    if status == "Завершен":
        return "Завершен"
    if "Перенесен" in status:
        return "Перенесен"
    if "Отменен" in status:
        return "Отменен"
    if ":" in status:
        return "Начало: " + status
    return "Live"


    
def get_result(first_team_goals, second_team_goals):
    if first_team_goals == '-':
        return "0-0"
    return first_team_goals + "-" + second_team_goals



def get_koeff(table):
    kefs = []
    for k in table[1:4]:
        k_kef = k.query_selector('.koeff').inner_text()
        kefs.append(k_kef)
    return kefs



def get_home_or_away(team_game, current_team):
    return team_game.query_selector('.result').eval_on_selector('.name', "(nodes, name) => nodes.innerText === name", current_team)



def get_score(game_page, left_team):
    scores = game_page.query_selector_all('.gls')
    if left_team:
        return {'scored':scores[0].inner_text(), 'missed':scores[1].inner_text()}
    else:
        return {'scored':scores[1].inner_text(), 'missed':scores[0].inner_text()}
    

    
def get_odds(game_page, left_team):

    bk_list = game_page.locator('.odds_logo').all()
    for bk in bk_list:
        odds = bk.locator('.odds_coeff').all()
        if len(odds[0].inner_text()) > 1:
            if left_team:
                return odds[0].inner_text()
            else:
                return odds[2].inner_text()
    return ' '
    

    
def get_shots(game_page, left_team):  

    shots = game_page.locator('.stats_item:has-text("Удары в створ")').locator('.stats_inf').all()
    if shots:
        if left_team:
            return {'shots':shots[0].inner_text(), 'shots_missed':shots[1].inner_text()}
        else:
            return {'shots':shots[1].inner_text(), 'shots_missed':shots[0].inner_text()}
    else:
        return {'shots':' ', 'shots_missed':' '}

def get_team_name(game, home = True):
    if home:
        return game.query_selector('.result').query_selector('.ht').query_selector('.name').query_selector('span').inner_text()
    else:
        return game.query_selector('.result').query_selector('.at').query_selector('.name').query_selector('span').inner_text()
    

def get_team_score(game, home=True):    
    if home:
        return game.query_selector('.result').query_selector('.ht').query_selector('.gls').inner_text()
    else:
        return game.query_selector('.result').query_selector('.at').query_selector('.gls').inner_text()
    

def get_last_10_games(team_games, game_page, team, context):
    result = []
    count = 1
    print(f'{team} Parsing last 10 games...')

    for team_game in team_games:
        
        left_team = get_home_or_away(team_game, team)


        score = get_score(team_game, left_team)

        team_game.query_selector('a[class="game_link"]').click()
        game_page.wait_for_selector('.modal')

        sleep(2)

        sublink = 'https://soccer365.ru' + game_page.get_by_text("Страница матча ►").get_attribute('href')
        game_page.locator('.active-modal').click(position={'x':0, 'y':0})

        sub_game_page = context.new_page()
        sub_game_page.goto(sublink)
    
        sleep(1)

        coeff = get_odds(sub_game_page, left_team)

        shots = get_shots(sub_game_page, left_team)

        result = result + [score['scored'], score['missed'], coeff, shots['shots'], shots['shots_missed']]         
        print(f'Game #{count}: ',score['scored'], score['missed'], coeff, shots['shots'], shots['shots_missed'])
        sub_game_page.close()
        count = count + 1
    return result


def run(playwright: Playwright, date):

    chromium = playwright.chromium

    browser = chromium.launch(headless=True)
    
    context = browser.new_context()
    page = context.new_page()

    page.goto(f"https://soccer365.ru/online/&date={date}")
    champs = page.query_selector_all('.live_comptt_bd')

    # для парсинга всех чемпионатов дня убрать [0:1] 
    for item in champs[0:1]:
        champ = item.query_selector('.block_header').query_selector('span').inner_text()
        games = item.query_selector_all('.game_block')
        for game in games:

            status = get_status(game)
            time = status[-5:]

            home_team = get_team_name(game)
            away_team = get_team_name(game, home = False)

            home_team_goals = get_team_score(game)
            away_team_goals = get_team_score(game, home = False)

            result = get_result(home_team_goals, away_team_goals)

            link = 'https://soccer365.ru' + game.query_selector('a[class="game_link"]').get_attribute('href')

            game_page = context.new_page()
            game_page.goto(link)

            kefs = get_koeff(game_page.query_selector('#widget_bk').query_selector_all('td'))

            game_page.get_by_text('Форма команд').click(delay=1000)

            home_team_games = game_page.query_selector('.live_block_hf').query_selector_all('.game_block')
            away_team_games = game_page.query_selector('.live_block_hf.right').query_selector_all('.game_block')

            home_last_10_games = get_last_10_games(home_team_games, game_page, home_team, context)
            away_last_10_games = get_last_10_games(away_team_games, game_page, away_team, context)
                                       

            row = [champ, time, home_team, away_team, result, status, *kefs, *home_last_10_games, *away_last_10_games]
            print(*row)

            with open('result.csv', 'a') as f:
                writer = csv.writer(f)
                writer.writerow(row)

            game_page.close()

    browser.close()
    

def validate_date(date):
    try:
        datetime.strptime(date, '%Y-%m-%d')
        return True
    except:
        print("Incorrect format")


if __name__ == '__main__':
    print('Enter dates (format: YYYY-MM-DD and press "Enter") and to finish input type - "ok"')
    dates = []
    
    s=""
    while s != "ok":
        s = input()
        if s != "ok":
            if validate_date(s):
                dates.append(s)
    
                
    for date in dates:
        with sync_playwright() as playwright:
            print("Running app...")
            run(playwright, date)

    
    