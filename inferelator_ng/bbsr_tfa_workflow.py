"""
Run BSubtilis Network Inference with TFA BBSR.
"""

import numpy as np
import os
from workflow import WorkflowBase
import design_response_translation #added python design_response
from tfa import TFA
from results_processor import ResultsProcessor
import mi_R
import bbsr_R
import datetime

class BBSR_TFA_Workflow(WorkflowBase):

    def run(self):
        """
        Execute workflow, after all configuration.
        """
        np.random.seed(self.random_seed)

        self.mi_clr_driver = mi_R.MIDriver()
        self.regression_driver = bbsr_R.BBSR_driver()
        self.design_response_driver = design_response_translation.PythonDRDriver() #this is the python switch
        self.get_data()
        self.compute_common_data()
        self.compute_activity()
        betas = []
        rescaled_betas = []

        for idx, bootstrap in enumerate(self.get_bootstraps()):
            print('Bootstrap {} of {}'.format((idx + 1), self.num_bootstraps))
            X = self.activity.ix[:, bootstrap]
            Y = self.response.ix[:, bootstrap]
            print('Calculating MI, Background MI, and CLR Matrix')
            (self.clr_matrix, self.mi_matrix) = self.mi_clr_driver.run(X, Y)
            print('Calculating betas using BBSR')
            current_betas, current_rescaled_betas = self.regression_driver.run(X, Y, self.clr_matrix, self.priors_data)
            betas.append(current_betas)
            rescaled_betas.append(current_rescaled_betas)
        self.emit_results(betas, rescaled_betas, self.gold_standard, self.priors_data)

    def compute_activity(self):
        """
        Compute Transcription Factor Activity
        """
        print('Computing Transcription Factor Activity ... ')
        TFA_calculator = TFA(self.priors_data, self.design, self.half_tau_response)
        self.activity = TFA_calculator.compute_transcription_factor_activity()

    def emit_results(self, betas, rescaled_betas, gold_standard, priors):
        """
        Output result report(s) for workflow run.
        """
        output_dir = os.path.join(self.input_dir, datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(output_dir)
        self.results_processor = ResultsProcessor(betas, rescaled_betas)
        self.results_processor.summarize_network(output_dir, gold_standard, priors)
