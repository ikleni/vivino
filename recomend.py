# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 15:52:37 2020.

@author: Alex Boivin
"""

import pandas as pd
import numpy as np
import random
from surprise import SVD
from surprise import Dataset
from surprise import accuracy
from surprise import Reader
from surprise.model_selection import LeaveOneOut, KFold
from surprise.model_selection import RandomizedSearchCV, cross_validate
import time
from collections import defaultdict
# from reco_utils.dataset.python_splitters import python_stratified_split
# from reco_utils.recommender.surprise.surprise_utils import predict, compute_ranking_predictions
# from reco_utils.evaluation.python_evaluation import (rmse, mae, rsquared, exp_var,\
#             map_at_k, ndcg_at_k, precision_at_k, recall_at_k, get_top_k_items)

    
class hyper_tune():
    """Use surprise RandomizedSearchCV to tune hyperparameters."""
    
    def __init__(self,data_ml,min_n_ratings=2,tune_method='rmse'):
        # self.data = combined_processed_wine_data
        # self.data_ml = Dataset.load_from_df(self.data, reader=Reader(rating_scale=(1,5)))
        self.data_ml = data_ml
        self.min_n_ratings = min_n_ratings
        self.tune_method = tune_method
        
    def __call__(self,min_n_ratings=2):
        
        print('Tuning...')
        # Seperate data into A and B sets for unbiased accuracy evaluation
        raw_ratings = self.data_ml.raw_ratings
        # shuffle ratings
        random.shuffle(raw_ratings)
        # A = 90% of the data, B = 10% of the data
        threshold = int(.9 * len(raw_ratings))
        A_raw_ratings = raw_ratings[:threshold]
        B_raw_ratings = raw_ratings[threshold:]
        # make data_ml the set A
        data_ml = self.data_ml
        data_ml.raw_ratings = A_raw_ratings  
        # search grid
        param_grid = {'n_factors': [50,100,150],'n_epochs': [30,50,70], 'lr_all': [0.002,0.005,0.01],'reg_all':[0.02,0.1,0.4,0.6]}
        gs = RandomizedSearchCV(SVD, param_grid, measures=['rmse', 'mae', 'fcp'], cv=5)
        # fit
        start_time = time.time()
        gs.fit(data_ml)
        search_time = time.time() - start_time
        print("Took {} seconds for search.".format(search_time))
        # best score
        print(gs.best_score[self.tune_method])
        # combination of parameters that gave the best RMSE score
        print(gs.best_params[self.tune_method])
        
        # get resulting algorithm with tunned parameters
        algo = gs.best_estimator[self.tune_method]
        
        # retrain on the whole set A
        trainset = data_ml.build_full_trainset()
        algo.fit(trainset)
        
        # Compute biased accuracy on A
        predictions = algo.test(trainset.build_testset())
        print('Biased accuracy,', end='   ')
        accuracy.rmse(predictions)
        accuracy.mae(predictions)
        accuracy.fcp(predictions)
        
        # Compute unbiased accuracy on B
        # make data_ml the set B
        testset = data_ml.construct_testset(B_raw_ratings)
        predictions = algo.test(testset)
        print('Unbiased accuracy,', end=' ')
        accuracy.rmse(predictions)
        accuracy.mae(predictions)
        accuracy.fcp(predictions)
        
        return(algo)
    
class wine_recomender():
    """Vivino collaborative filtering recomender system."""
    
    def __init__(self,processed_wine_data,tune=False):
        
        self.tune = tune
        self.data = processed_wine_data.combined_ratings_from_filtered_users_data
        self.data_ml = Dataset.load_from_df(self.data, reader=Reader(rating_scale=(1,5)))
        # self.data['Wine'] = self.data[['Winery','WineName']].apply(' - '.join,axis=1)
        # self.data = self.data[['Username','Wine','Rating']]
        
        # Cross validation
        # if tune, always compare tunned and un-tunned cross-validation results
        if self.tune:
            tunner = hyper_tune(self.data_ml)
            tunned_algo = tunner()
            # cross-validate with 4 folds corresponding to a 75/25 split
            # cross_validate(tunned_algo, self.data_ml, measures=['RMSE', 'MAE'], cv=4, verbose=True)
        algo = SVD()
        # cross_validate(algo, self.data_ml, measures=['RMSE', 'MAE'], cv=4, verbose=True)
        
        # cross-validate with 5 folds corresponding to a 80/20 split
        kf = KFold(n_splits=5)
        
        for trainset, testset in kf.split(self.data_ml):
            # train and test algorithm
            if self.tune:
                start_time = time.time()
                tunned_algo.fit(trainset)
                train_time = time.time() - start_time
                print("Took {} seconds for tunned training.".format(train_time))
                start_time = time.time()
                tunned_predictions = tunned_algo.test(testset)
                test_time = time.time() - start_time
                print("Took {} seconds for tunned testing.".format(test_time))    
            start_time = time.time()
            algo.fit(trainset)
            train_time = time.time() - start_time
            print("Took {} seconds for un-tunned training.".format(train_time))
            start_time = time.time()
            global predictions
            predictions = algo.test(testset)
            test_time = time.time() - start_time
            print("Took {} seconds for un-tunned testing.".format(test_time))
            
            # compute metrics
            if self.tune:
                accuracy.rmse(tunned_predictions, verbose=True)
                tunned_precisions, tunned_recalls = self.precision_recall_at_k(tunned_predictions, k=5, threshold=3.5)
                # Precision and recall can then be averaged over all users
                print(sum(prec for prec in tunned_precisions.values()) / len(tunned_precisions))
                print(sum(rec for rec in tunned_recalls.values()) / len(tunned_recalls))
            accuracy.rmse(predictions, verbose=True)
            precisions, recalls = self.precision_recall_at_k(predictions)
            # Precision and recall can then be averaged over all users
            print(sum(prec for prec in precisions.values()) / len(precisions))
            print(sum(rec for rec in recalls.values()) / len(recalls))
            
        # Make recomendations
        # only recomend using tunned OR un-tunned algorithm
        full_trainset = self.data_ml.build_full_trainset()
        if self.tune:
            start_time = time.time()
            tunned_algo.fit(full_trainset)
            train_time = time.time() - start_time
            print("Took {} seconds for tunned full training.".format(train_time))
        else:
            start_time = time.time()
            algo.fit(full_trainset)
            train_time = time.time() - start_time
            print("Took {} seconds for un-tunned full training.".format(train_time))
        
        # all user-item pairs with no rating in the trainset
        anti_testset = trainset.build_anti_testset()
        if self.tune:
            start_time = time.time()
            predictions = tunned_algo.test(anti_testset)
            test_time = time.time() - start_time
            print("Took {} seconds for tunned predictions.".format(test_time))    
        else:
            start_time = time.time()
            predictions = algo.test(anti_testset)
            test_time = time.time() - start_time
            print("Took {} seconds for un-tunned predictions.".format(test_time))    
            
        # Get top-n predictions for all users
        self.top_n_items, self.top_n_items_pd = self.get_top_n(predictions, n=5)
        
    def precision_recall_at_k(self,predictions, k=5, threshold=3.5):
        """Return precision and recall at k metrics for each user."""
    
        # First map the predictions to each user.
        user_est_true = defaultdict(list)
        for uid, _, true_r, est, _ in predictions:
            user_est_true[uid].append((est, true_r))
    
        precisions = dict()
        recalls = dict()
        for uid, user_ratings in user_est_true.items():
    
            # Sort user ratings by estimated value
            user_ratings.sort(key=lambda x: x[0], reverse=True)
    
            # Number of relevant items
            n_rel = sum((true_r >= threshold) for (_, true_r) in user_ratings)
    
            # Number of recommended items in top k
            n_rec_k = sum((est >= threshold) for (est, _) in user_ratings[:k])
    
            # Number of relevant and recommended items in top k
            n_rel_and_rec_k = sum(((true_r >= threshold) and (est >= threshold))
                                  for (est, true_r) in user_ratings[:k])
    
            # Precision@K: Proportion of recommended items that are relevant
            precisions[uid] = n_rel_and_rec_k / n_rec_k if n_rec_k != 0 else 1
    
            # Recall@K: Proportion of relevant items that are recommended
            recalls[uid] = n_rel_and_rec_k / n_rel if n_rel != 0 else 1
    
        return precisions, recalls
    
    def get_top_n(self,predictions, n=5):
        """Return the top-N recommendation for each user from a set of predictions.
    
        Args:
            predictions(list of Prediction objects): The list of predictions, as
                returned by the test method of an algorithm.
            n(int): The number of recommendation to output for each user. Default
                is 10.
    
        Returns:
        A dict where keys are user (raw) ids and values are lists of tuples:
            [(raw item id, rating estimation), ...] of size n.
        """
    
        # First map the predictions to each user.
        top_n = defaultdict(list)
        for uid, iid, true_r, est, _ in predictions:
            top_n[uid].append((iid, est))
    
        # Then sort the predictions for each user and retrieve the k highest ones.
        for uid, user_ratings in top_n.items():
            user_ratings.sort(key=lambda x: x[1], reverse=True)
            top_n[uid] = user_ratings[:n]
            
        # Convert to DataFrame
        top_n_pd = pd.DataFrame(columns=['Username', 'Wine', 'est'])
        for uid, val in top_n.items():
            for subval in val:
                iid, est = subval
                values_to_add = {'Username':uid,'Wine':iid,'est':est}
                row_to_add = pd.Series(values_to_add)
                top_n_pd = top_n_pd.append(row_to_add,ignore_index=True)
    
        return top_n, top_n_pd

        
class processed_wine_data():
    """Filter data from wine_data instance."""
    
    def __init__(self,wine_data,min_number_of_reviews=10):
        """
        Filter data from wine_data instance.

        Parameters
        ----------
        wine_data : TYPE
            DESCRIPTION.
        min_number_of_reviews : TYPE, optional
            DESCRIPTION. The default is 3.

        Returns
        -------
        None.

        """
        # Parameters
        self.wine_data = wine_data
        self.min_number_of_reviews = min_number_of_reviews
        
        # Attributes
        clean_results = self._clean_data()
        self.num_scraped_reviews = clean_results[0]
        self.num_cleaned_reviews = clean_results[1]
        self.num_wines = clean_results[2]
        self.num_unique_users = clean_results[3]
        self.num_users_with_multiple_interactions = clean_results[4]
        self.num_ratings_from_filtered_users = clean_results[5]
        self.cleaned_review_data = clean_results[6]
        self.ratings_from_filtered_users_data = clean_results[7]
        self.combined_ratings_from_filtered_users_data = clean_results[8]
        
        
    def _clean_data(self):
        """
        Clean review data.
        
        Removes nans and blank user names, 
        avaeraging reviews for users who rated the same wine multiple
        times, and removing anonymous reviews. Then only keep reviews from
        users with at least min_number_of_reviews.

        Returns
        -------
        total_scraped_reviews : TYPE
            DESCRIPTION.
        TYPE
            DESCRIPTION.
        wine_count : TYPE
            DESCRIPTION.
        TYPE
            DESCRIPTION.
        TYPE
            DESCRIPTION.
        TYPE
            DESCRIPTION.
        cleaned_review_data_df : TYPE
            DESCRIPTION.
        ratings_from_filtered_users_df : TYPE
            DESCRIPTION.

        """
        total_scraped_reviews = len(self.wine_data.review_data)
        print('Total scraped reviews: {}'.format(total_scraped_reviews))
        # Keep data only from users who have made multiple reviews
        # average ratings for users who rated same wine multiple times. also removes nans and blank names
        cleaned_review_data_df = self.wine_data.review_data.groupby(['Username','WineName','Winery'],as_index=False).mean()
        # remove anonymous reviews
        anonymous_index_vals = cleaned_review_data_df[cleaned_review_data_df['Username'] == 'Vivino User'].index
        cleaned_review_data_df.drop(anonymous_index_vals,inplace=True)
        print('Total cleaned reviews: {}'.format(len(cleaned_review_data_df)))
        # count number of wines
        wine_count = len(cleaned_review_data_df.groupby(['WineName','Winery']).size())
        print('Total wines: {}'.format(wine_count))
        # count the unique users
        user_reviews_count_df = cleaned_review_data_df.groupby(['Username','WineName','Winery']).size().groupby(['Username']).size()
        print('Total unique users: {}'.format(len(user_reviews_count_df)))
        # find the users with multiple reviews
        users_with_multiple_interactions_df = user_reviews_count_df[user_reviews_count_df >= self.min_number_of_reviews].reset_index()[['Username']]
        print('Users with at least {min_rev} reviews: {usr_count}'.format(min_rev=self.min_number_of_reviews,usr_count=len(users_with_multiple_interactions_df)))
        # keep only the reviews from users with multiple reviews
        ratings_from_filtered_users_df = cleaned_review_data_df.merge(users_with_multiple_interactions_df,how='right',left_on=['Username'],right_on=['Username'])
        print('Reviews from users with at least {min_rev} reviews: {rev_count}'.format(min_rev=self.min_number_of_reviews,rev_count=len(ratings_from_filtered_users_df)))
        # combine winery and winename columns into a single wine column
        combined_ratings_from_filtered_users_df = ratings_from_filtered_users_df
        combined_ratings_from_filtered_users_df['Wine'] = combined_ratings_from_filtered_users_df[['Winery','WineName']].apply(' - '.join,axis=1)
        combined_ratings_from_filtered_users_df = combined_ratings_from_filtered_users_df[['Username','Wine','Rating']]
        
        
        
        return total_scraped_reviews, len(cleaned_review_data_df), wine_count,\
            len(user_reviews_count_df), len(users_with_multiple_interactions_df),\
            len(ratings_from_filtered_users_df), cleaned_review_data_df,\
            ratings_from_filtered_users_df, combined_ratings_from_filtered_users_df
            