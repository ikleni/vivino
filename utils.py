import numpy as np
import json
import requests


headers = {
    "User-Agent": "Mozilla/5.0",
}

def map_wine_info_to_json(raw_text):


    if 'window.__PRELOADED_STATE__.vintagePageInformation = ' in raw_text:
        text = raw_text.split('window.__PRELOADED_STATE__.vintagePageInformation = ')[1].split(';\n')[0]
    else:
        text = raw_text.split('window.__PRELOADED_STATE__.offerPageInformation = ')[1].split('\n  window.__PRELOADED_STATE__.winePageType = "offersPage"')[0] 

    d = json.loads(text)
    
    # might have to add this if it opens a page of a wine and not a specific vintage
    # 'window.__PRELOADED_STATE__.winePageInformation = ' , ';/n'

    return d

def search_dict_element(dct, key_chain):
    
    tmp_element = dct.copy()
    try: 
        for key in key_chain:
            tmp_element = tmp_element[key]

    except KeyError:
        tmp_element = np.nan
    
    except TypeError:
        tmp_element = np.nan

    return tmp_element

def get_reviews_for_vintage(wine_id, wine_year, n_reviews):

    api_url = (
    "https://www.vivino.com/api/wines/{id}/reviews?per_page=50&year={year}")

    N_pages = n_reviews//50 # max(n_reviews//50, 20)

    reviews_json = []
    for i in range(N_pages):

        data = requests.get(api_url.format(id=wine_id, year = wine_year), params = {"page": i + 1}, headers=headers).json()['reviews']
        
        if len(data) > 0:

            for review in data:
                
                # only keep english reviews
                if search_dict_element(review, ['language']) == 'en':

                    review_dict = {
                        'wine_id' : wine_id,
                        'wine_year': wine_year,
                        'reviewed_wine_id' : search_dict_element(review, ['vintage','id']),
                        'reviewed_wine_seoname' : search_dict_element(review, ['vintage', 'seo_name']), 
                        'review_id': search_dict_element(review, ['id']),
                        'rating'   : search_dict_element(review, ['rating']),
                        'txt'   : search_dict_element(review, ['note']),
                        'lang'   : search_dict_element(review, ['language']),
                        'date'   : search_dict_element(review, ['created_at']),
                        'is_agg'   : search_dict_element(review, ['aggregated']),
                        'user_id' : search_dict_element(review, ['user', 'id']),
                        'user_name' : search_dict_element(review, ['user', 'seo_name']),
                        'user_feat' : search_dict_element(review, ['user', 'is_featured']),
                        'user_premium': search_dict_element(review, ['user', 'is_premium']),
                        'user_nfollowers': search_dict_element(review, ['user', 'statistics', 'followers_count']),
                        'user_nfollowing': search_dict_element(review, ['user', 'statistics', 'followings_count']),
                        'user_nratings_cnt': search_dict_element(review, ['user', 'statistics', 'ratings_count']),
                        'user_nratings_sum': search_dict_element(review, ['user', 'statistics', 'ratings_sum']),
                        'user_nreviews': search_dict_element(review, ['user', 'statistics', 'reviews_count']),
                        'user_npurchases': search_dict_element(review, ['user', 'statistics', 'purchase_order_count']),

                    }

                    reviews_json.append(review_dict)
                    
                else:
                    pass

    return reviews_json
    

    
######################################################
######################################################
######################################################
######################################################
################ Parsing JSON file ###################
######################################################
######################################################
######################################################
######################################################
# copied from //Wine/Code/Scraping.py


def get_flavor_keyword_info(data, n_flavor_groups = 2, n_keywords = 1):

    results_dict = {}

    # check how many flavors are present
    flavor_info = search_dict_element(data, ['vintage', 'wine', 'taste', 'flavor'])

    if type(flavor_info) == list:

        n_flavors = len(flavor_info)

        for n in range(min(n_flavors, n_flavor_groups)):
            
            flavor_info_n = flavor_info[n]
            results_dict[f'flavor_group_{n}']       = search_dict_element(flavor_info_n, ['group'])
            results_dict[f'flavor_group_{n}_count'] = search_dict_element(flavor_info_n, ['stats', 'count'])

            flavor_n_prim_keywords = search_dict_element(flavor_info_n, ['primary_keywords'])
            flavor_n_scnd_keywords = search_dict_element(flavor_info_n, ['secondary_keywords'])

            if type(flavor_n_prim_keywords) == list:    

                for i in range(min(len(flavor_n_prim_keywords),n_keywords)):

                    results_dict[f'flavor_group_{n}_prim_keyword_{i}'] = flavor_n_prim_keywords[i]['name']
                    results_dict[f'flavor_group_{n}_prim_keyword_{i}_count'] = flavor_n_prim_keywords[i]['count']

            if type(flavor_n_scnd_keywords) == list:    

                for i in range(min(len(flavor_n_scnd_keywords),n_keywords)):

                    results_dict[f'flavor_group_{n}_scnd_keyword_{i}'] = flavor_n_scnd_keywords[i]['name']
                    results_dict[f'flavor_group_{n}_scnd_keyword_{i}_count'] = flavor_n_scnd_keywords[i]['count']

    return results_dict

        

def get_ratings_info(data):
    
    output_dict         = {}
    rating_names_input  = ['ratings_count', 'ratings_average', 'labels_count', 'wine_ratings_count', 'wine_ratings_average', 'wine_status']
    rating_names_output = ['upc_ratings_count', 'upc_ratings_avg', 'labels_count', 'wine_ratings_count', 'wine_ratings_avg', 'wine_status']
    # num ratings is essentially the number of reviews based on website inspection

    try:

        if ('vintage' in data.keys())&('statistics' in data['vintage'].keys()):

            for inp_name,out_name in zip(rating_names_input, rating_names_output):

                if inp_name in data['vintage']['statistics'].keys():

                    output_dict[out_name] = data['vintage']['statistics'][inp_name]

                else:
                    output_dict[out_name] = np.nan
    except KeyError:

        for out_name in rating_names_output:
                    output_dict[out_name] = np.nan

    return output_dict


def get_taste_info(data):

    output_dict = {}

    taste_names_input  = ['acidity', 'fizziness', 'intensity', 'sweetness', 'tannin']
    taste_names_output = ['acidity', 'fizziness', 'intensity', 'sweetness', 'tannin']

    try:
        if ('vintage' in data.keys())&('wine' in data['vintage'].keys()) & ('taste' in data['vintage']['wine'].keys()) & ('structure' in data['vintage']['wine']['taste'].keys()) & (type(data['vintage']['wine']['taste']['structure']) == dict):

            for inp_name,out_name in zip(taste_names_input, taste_names_output):

                if inp_name in data['vintage']['wine']['taste']['structure'].keys():

                    output_dict[out_name] = data['vintage']['wine']['taste']['structure'][inp_name]

                else:
                    output_dict[out_name] = np.nan
        else: 
            for out_name in taste_names_output:
                    output_dict[out_name] = np.nan

    except KeyError:
        for out_name in taste_names_output:
                    output_dict[out_name] = np.nan


    # taste info from another subset of the dict (useful if the primary source of data is missing)
    
    additional_taste_dict = {

    'style_id' : search_dict_element(data, ['vintage', 'wine', 'style', 'id']),
    'style_reg_name' : search_dict_element(data, ['vintage', 'wine', 'style', 'regional_name']),
    'style_var_name' : search_dict_element(data, ['vintage', 'wine', 'style', 'varietal_name']),
    'style_name' : search_dict_element(data, ['vintage', 'wine', 'style', 'name']),
    'style_body' : search_dict_element(data, ['vintage', 'wine', 'style', 'body']),
    'style_body_desc' : search_dict_element(data, ['vintage', 'wine', 'style', 'body_description']),
    'style_acid' : search_dict_element(data, ['vintage', 'wine', 'style', 'acidity']),
    'style_acid_desc' : search_dict_element(data, ['vintage', 'wine', 'style', 'acidity_description']),

    }

    output_dict = {**output_dict, **additional_taste_dict}

    return output_dict

def get_price_info(data):

    output_dict = {
    'price': search_dict_element(data, ['price', 'amount']), 
    'discount_percent': search_dict_element(data, ['price', 'discount_percent']), 
    'bottle_type': search_dict_element(data, ['price', 'bottle_type', 'id'])
    }

    return output_dict

def get_essential_wine_info(data):

    # if anything here is missing it is reasonable to drop this wine

    output_dict = {
                        
    'upc_id' : search_dict_element(data, ['vintage', 'id']),
    'upc_name': search_dict_element(data, ['vintage', 'seo_name']),
    'upc_year': search_dict_element(data, ['vintage', 'year']),
    'wine_id' : search_dict_element(data, ['vintage', 'wine', 'id']),
    'wine_name': search_dict_element(data, ['vintage', 'wine', 'name']),
    'region_id': search_dict_element(data, ['vintage', 'wine', 'region', 'id']), 
    'region_name': search_dict_element(data, ['vintage', 'wine', 'region', 'name']),
    'country_name': search_dict_element(data, ['vintage', 'wine', 'region', 'country', 'code']),
    'winery_id': search_dict_element(data, ['vintage', 'wine', 'winery', 'id']), 
    'winery_name': search_dict_element(data, ['vintage', 'wine', 'winery', 'name']),

    }
    
    # not very reliable for blends... (the order of grapes does not correspond to share in wine)
    grapes_data = search_dict_element(data, ['vintage', 'wine', 'style', 'grapes'])
    
    if type(grapes_data) == list:
        n_grapes = len(grapes_data)

        if n_grapes > 0:
            top_grape_id   = search_dict_element(grapes_data[0], ['id'])  
            top_grape_name = search_dict_element(grapes_data[0], ['name'])

        else:
            top_grape_id   = np.nan
            top_grape_name = np.nan
    else:
        n_grapes       = np.nan
        top_grape_id   = np.nan
        top_grape_name = np.nan
    
    output_dict['n_grapes']         = n_grapes
    output_dict['top_grape_id']     = top_grape_id
    output_dict['top_grape_name']   = top_grape_name

    return output_dict


def unpack_vivino_json(data, n_flavor_groups = 2, n_keywords = 1):

    # essential information
    essential_data = get_essential_wine_info(data)

    # price information
    price_data     = get_price_info(data)

    # ratings information
    ratings_data   = get_ratings_info(data)

    # taste vector information
    taste_data     = get_taste_info(data)

    # flavor text keywords
    flavor_data    = get_flavor_keyword_info(data, n_flavor_groups = n_flavor_groups, n_keywords = n_keywords)

    all_data       = {**essential_data, **price_data, **ratings_data, **taste_data, **flavor_data}

    # essential_info_names = list(essential_data.keys())

    return all_data