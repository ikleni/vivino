# -*- coding: utf-8 -*-
"""
Created on Tue May 2 11:11:11 2023.

@author: Vanya Klenovskiy
"""
from utils import *
from selenium.webdriver import Firefox
from selenium.webdriver import Chrome
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import pandas as pd
import re
import os
import datetime
from timeit import default_timer as timer
import glob

# search for all red wines between 10-40$ with a rating of 3.5 or above
# URL = 'https://www.vivino.com/explore?e=eJwNyUEKgCAQBdDb_LVC21lE3SIiJptESI1RrG6fm7d5UckihkTWIPJLg4H7aBrhOjPuvv6kxhqk8oW8k3INyZeNmyh7QaZDisNTl5XsD-oNGk4='
# search for all red wines between 10-25$ with a rating of 3.5 or above
# URL = 'https://www.vivino.com/explore?e=eJwNxEEKgCAUBcDbvGVk4fItom4RET8zEdLCxOr2NYsJiW2lEXykqhHkYaNhXvYdzN-AkwpuY5HkbZYdx8Ik2Ud3zVJsEmdxcLWXwZ3HieoDC54atg=='
# search for all red wines
# URL = 'https://www.vivino.com/explore?e=eJzLLbI1VMvNzLM1UMtNrLA1NTBQS660DQ1WSwYSLmoFQNn0NNuyxKLM1JLEHLX8ohRbtfykSlu18pLoWKBksW1aDgDa9hW8'
# search for all french wines
URL = 'https://www.vivino.com/explore?e=eJzLLbI1VMvNzLM1UMtNrLA1NTBQS660DQ1WSwYSLmoFQNn0NNuyxKLM1JLEHLX8ohRbtfykSlu18pLoWKBkcmUxkE4rUiu2TcsBAK-iGP4%3D'
# aragonez_wines
URL = 'https://www.vivino.com/explore?e=eJzLLbI10TNSy83MszVQy02ssDUzUEuutA0NVksGEi5qBbaGaulptmWJRZmpJYk5avlFKbZq-UmVtmrlJdGxIEkQaWSuVmwbEgEAnrAX5g%3D%3D' 


# number of seconds to wait before each scroll when infinite scrolling to botom
# may not get to the botom if too short
SCROLL_PAUSE_TIME = 1

class element_present_after_scrolling():
    """
    A custom selenium expectation for scrolling until an element is present.
    
    Thanks to MP https://medium.com/@randombites/how-to-scroll-while-waiting-for-an-element-20208f65b576
    
    Parameters
    ----------
    locator : tuple
        Used to find the element.
        
    Returns
    -------
    elements : WebElement 
        Once it has the particular element.
        
    """
    
    def __init__(self, locator, driver):
        """Attributes."""
        self.locator = locator
        self.driver = driver
        
    def __call__(self, driver):
        """Scroll by 500px increments."""
        elements = driver.find_elements(*self.locator)   # Finding the referenced element
        if len(elements) > 0:
            return elements
        else:
            self.driver.execute_script("window.scrollBy(0, 500);")
            
class wine_data():
    """Scrape wine data and reviews from Vivino."""
    
    def __init__(self,scroll_to_bottom=True,save_path=None,timeout=20,\
                 no_scrape=False):
        """
        Scrape data using selenium with Firefox and store as a pandas DataFrame.

        Parameters
        ----------
        scroll_to_bottom : bool, optional
            If True scroll to bottom of the search page to get all the results.
            The default is False.
            
        save_path : NoneType or str, optional
            If a file path is provided, save the wine and review data to csv.
            The default is None.
            
        timeout : int
            Timeout in seconds for page load checks. The default is 20.
            
        no_scrape : bool or str, optional
            If not False, read in pre-scraped .csv format data instead of 
            scraping new data. If not False, must be folder path to both 
            wine_data and review_data csv files. This folder must contain only 
            one of each of wine_data and review_data csv files. File name 
            format must be wine_file*.csv and review_file*.csv. 
            The default is False.

        Attributes
        ----------
        number_of_results : int
            Number of search results.
            
        wine_data : DataFrame
            Collected wine data.
            
        results_data : DataFrame
            Collected review data.

        Returns
        -------
        None.

        """
        # Parameters
        self.timeout = timeout # timeout for page load checks
        self.scroll_to_bottom = scroll_to_bottom
        self.save_path = save_path
        self.no_scrape = no_scrape
        
        # if no_scrape is false, scrape Vivino
        if not self.no_scrape:
            # opts = Options()
            # opts.headless = True #use a headless browser
            self.driver = Chrome() # options=opts
            self.driver.get(URL)
            
            # check that page has loaded
            try:
                element_present = EC.presence_of_element_located((By.CLASS_NAME,\
                                    'querySummary__querySummary--39WP2'))
                WebDriverWait(self.driver, self.timeout).until(element_present)
            except TimeoutException:
                print("Timed out waiting for page to load")
            
            time.sleep(SCROLL_PAUSE_TIME + 2)

            # get main window handle 
            self._main_window = self.driver.current_window_handle
            # get number of results
            number_of_results = self.driver.find_element(By.CLASS_NAME,'querySummary__querySummary--39WP2').text
            self.number_of_results = int(re.findall('\d+',number_of_results)[0]) # extract number of results using regular expressions
            print("Found {} wines.".format(self.number_of_results))
        
            
            if self.scroll_to_bottom:
                self._infinity_scroll()
                # time.sleep(self.number_of_results//SCROLL_PAUSE_TIME + 1)
            
            self.wine_data, self.review_data = self._get_wine_info()
            
            # save to .csv if a path is provided
            if self.save_path:
                date = str(datetime.date.today())
                filename_wine = 'wine_data_' + date + '.csv'
                filename_review = 'review_data_' + date + '.csv'
                filepath_wine = os.path.join(self.save_path,filename_wine)
                filepath_review = os.path.join(self.save_path,filename_review)
                self.wine_data.to_csv(filepath_wine)
                self.review_data.to_csv(filepath_review)

        else: # open pre-scraped data
            filepath_wine = os.path.join(self.no_scrape,'wine_data*.csv')
            filepath_review = os.path.join(self.no_scrape,'review_data*.csv')
            # check to make sure folder only contains on set of data files
            wine_file_loc = glob.glob(filepath_wine)
            review_file_loc = glob.glob(filepath_review)
            if len(wine_file_loc) > 1 or len(review_file_loc) > 1:
                raise Exception('More than 1 wine_file*.csv and/or review_file*.csv in folder.')
            else: # open files
                self.wine_data = pd.read_csv(wine_file_loc[0],index_col=0)
                self.review_data = pd.read_csv(review_file_loc[0],index_col=0)
                
    def _infinity_scroll(self,element=False):
        """
        Infinite scroll to bottom of a page or element. Breaks when done.

        Parameters
        ----------
        element : WebElement, optional
            WebElement to scroll to the botom of instead of the whole page. The 
            default is False.

        Returns
        -------
        None.

        """
        if element: # scroll the page if no element is provided
            el = element
        else:
            el = self.driver.find_element(By.CLASS_NAME,'inner-page')
        # Get scroll height
        last_height = self.driver.execute_script\
            ("return arguments[0].scrollHeight", el)
        while True:
            # Scroll down to bottom
            if element: #scroll the element
                self.driver.execute_script\
                    ('arguments[0].scrollTop = arguments[0].scrollHeight', el)
            else: #scroll the window
                self.driver.execute_script\
                    ("window.scrollTo(0, arguments[0].scrollHeight);", el)
        
            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)
        
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script\
                ("return arguments[0].scrollHeight", el)
            if new_height == last_height:
                break #break at the bottom
            last_height = new_height

    def _get_wine_info(self):
        """
        Iterate through tabs and scrape data.

        Returns
        -------
        wine_data : DataFrame
            Collected wine data.
            
        results_data : DataFrame
            Collected review data.

        """
        # start timing the scraping process
        start = timer()
        print("Starting scrape...")
        discover_wines = self.driver.find_elements(By.XPATH, "//div[@class='wineCard__wineCard--2dj2T wineCard__large--1tkVl']")
        global wine_dict_list # global in case of premature end of run
        global review_dict_list
        wine_dict_list = []
        review_dict_list = []
        
        for i, wine in enumerate(discover_wines):
            # open wine page in new tab
            attempts = 0
            while attempts < 100: # in case of connection issue
                try:
                    ActionChains(self.driver).move_to_element(wine).perform()
                    ActionChains(self.driver).key_down(Keys.COMMAND).click(wine).key_up(Keys.COMMAND).perform()
                    # switch to latest tab (firefox always opens a new tab next to the main tab)
                    self.driver.switch_to.window(self.driver.window_handles[1]) 
                    # make sure top of page is loaded
                    element_present = EC.presence_of_element_located\
                        ((By.CLASS_NAME, 'inner-page'))
                    WebDriverWait(self.driver, self.timeout).until(element_present)
                    break
                except TimeoutException:
                    attempts += 1
                    self.driver.close() # close the unloaded tab
                    self.driver.switch_to.window(self._main_window) # back to main window
                    print("Timed out waiting for wine tab to load")
                    time.sleep(10) # wait for 10 seconds 
            
            time.sleep(2)

            raw_info  = self.driver.find_element(By.XPATH, "//div[@id='wine-page-lower-section']/following::script").get_attribute('innerHTML')
            wine_json = map_wine_info_to_json(raw_info)
            print(wine_json['vintage']['wine']['name'])
            print(wine_json['vintage']['wine']['id'])
            print(wine_json['vintage']['year'])
            wine_dict = unpack_vivino_json(wine_json)
            wine_dict_list.append(wine_dict)

            ## get reviews through API

            # initialise names for API request
            N_ratings = wine_json['vintage']['statistics']['ratings_count'] 
            wine_id   = wine_json['vintage']['wine']['id'] 
            wine_year = wine_json['vintage']['year']

            reviews_list      =  get_reviews_for_vintage(wine_id, wine_year, N_ratings)
            review_dict_list += reviews_list

            # # get reviews via scrolling

            # # if show more reviews button is below the loaded page, scroll until it loads
            # try:
            #     element_present = element_present_after_scrolling((By.CLASS_NAME,\
            #         'anchor__anchor--3DOSm.communityReviews__showAllReviews--1e12c.anchor__vivinoLink--29E1-'),\
            #                                                       self.driver)
            #     WebDriverWait(self.driver, self.timeout).until(element_present)
            # except TimeoutException:
            #     print("Timed out waiting for show more reviews button")
            
            # review_link = self.driver.find_element(By.CLASS_NAME,'anchor__anchor--3DOSm.communityReviews__showAllReviews--1e12c.anchor__vivinoLink--29E1-')
            # review_link.click()
            # try: #make sure review popup has loaded
            #     element_present = EC.presence_of_element_located\
            #         ((By.CLASS_NAME, 'allReviews__reviews--EpUem'))
            #     WebDriverWait(self.driver, self.timeout).until(element_present)
            # except TimeoutException:
            #     print("Timed out waiting for review popup to load")
            # review_pane = self.driver.find_element(By.CLASS_NAME,'baseModal__window--3r5PC.baseModal__themeNoPadding--T_ROG')
            # # scroll to the botom of the reviews
            # self._infinity_scroll(element=review_pane)
            # # get review info
            # discover_reviews = self.driver.find_element(By.CLASS_NAME, 'reviewCard__reviewContainer--1kMJM')
            # # discard last 3 since they are duplicates
            # discover_reviews = discover_reviews[:-3]
            # # print what tab we are on
            # for review in discover_reviews:
            #     user_name = review.find_element(By.CLASS_NAME, 'anchor__anchor--3DOSm.reviewCard__userName--2KnRl').text
            #     rating_elem = review.find_element(By.CLASS_NAME, 'rating__rating--ZZb_x')
            #     rating = float(rating_elem.get_attribute("aria-label").split()[1])
            #     review_dict = {'Username':user_name,'WineName':wine_name,\
            #                    'Winery':winery_name,'Rating':rating}
            #     review_dict_list.append(review_dict)
            # print('Completed wine {tab_num} of {tab_total}. Scrapabale reviews: {rev_num}'\
            #   .format(tab_num=i+1,tab_total=len(discover_wines),\
            #           rev_num=len(discover_reviews)))
            

            
            self.driver.close() # close the tab when done
            self.driver.switch_to.window(self._main_window)
            time.sleep(1) # pause for 1 second 
            
        wine_data = pd.DataFrame(wine_dict_list)
        review_data = pd.DataFrame(review_dict_list) 
        self.driver.close() # close browser when done
        # end the timer
        end = timer() 
        m, s = divmod(end - start, 60)
        h, m = divmod(m, 60)
        time_str = "Scraping took: %02d:%02d:%02d" % (h, m, s)
        print(time_str)
            
        return wine_data , review_data
        
        


# lazy load that's was used by someone to get food pairings
# driver = webdriver.Chrome()
# driver.get('https://www.vivino.com/US-TX/en/villa-maria-auckland-private-bin-sauvignon-blanc/w/39034?year=2021&price_id=26743464')
# driver.implicitly_wait(10)
# page_height = driver.execute_script("return document.body.scrollHeight")
# browser_window_height = driver.get_window_size(windowHandle='current')['height']
# current_position = driver.execute_script('return window.pageYOffset')
# while page_height - current_position > browser_window_height:
#     driver.execute_script(f"window.scrollTo({current_position}, {browser_window_height + current_position});")
#     current_position = driver.execute_script('return window.pageYOffset')
#     sleep(1)  # It is necessary here to give it some time to load the content
# print(driver.find_element(By.XPATH, '//div[@data-testid="mentions"]').text)
# driver.quit()