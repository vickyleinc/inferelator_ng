"""
Compute Bayesian Best Subset Regression by running R script
"""

import os
from . import utils
import pandas as pd

BBSR_module = utils.local_path("R_code", "bayesianRegression.R")

R_template = r"""
library('Matrix')
if ('parallel' %in% installed.packages()[, 'Package']) {{
  library('parallel')
}} else {{
  library('multicore')
}}

source('{module}')

X <- read.table('{X_file}', sep = ',', header = 1, row.names = 1)
Y <- read.table('{Y_file}', sep = ',', header = 1, row.names = 1)
clr.mat <- read.table('{clr_file}', sep = ',', header = 1, row.names = 1, check.names=FALSE)
prior.mat <- read.table('{priors_file}', sep = ',', header = 1, row.names = 1, check.names=FALSE)

nS <- {n}
cores <- {cores}
no.pr.weight <- {no_prior_weight}
prior.weight <- {prior_weight} # prior weights has to be larger than 1 to have an effect

weights.mat <- prior.mat * 0 + no.pr.weight
weights.mat[prior.mat != 0] <- prior.weight

x <- BBSR(X, Y, clr.mat, nS, no.pr.weight, weights.mat, 
                prior.mat, cores)

# Made a change here: replaced gp.out$tf.names with colnames(prior.mat)
bs.betas <- Matrix(0, nrow(Y), length(colnames(prior.mat)), 
                       dimnames=list(rownames(Y), colnames(prior.mat)))
bs.betas.resc <- bs.betas
for (res in x) {{
      bs.betas[res$ind, rownames(X)[res$pp]] <- res$betas
      bs.betas.resc[res$ind, rownames(X)[res$pp]] <- res$betas.resc
}}

write.table(as.matrix(bs.betas), '{betas_file}', sep = '\t')
write.table(as.matrix(bs.betas.resc), '{betas_resc_file}', sep = '\t')
cat("done. \n")
"""

def save_R_driver(to_filename, n, cores, no_prior_weight,
        prior_weight, X_file, Y_file, priors_file, clr_file,
        betas_file, betas_resc_file, module=BBSR_module):
    assert os.path.exists(module), "doesn't exist " + repr(module)
    text = R_template.format(
                X_file=X_file, Y_file=Y_file, module=module, n=n, cores=cores,
                prior_weight=prior_weight, no_prior_weight=no_prior_weight,
                betas_file=betas_file, betas_resc_file=betas_resc_file,
                clr_file=clr_file, priors_file=priors_file)
    with open(to_filename, "w") as outfile:
        outfile.write(text)
    return (to_filename, betas_file, betas_resc_file)

class BBSR_driver(utils.RDriver):

    X_file = "X.csv"
    Y_file = "Y.csv"
    priors_file = "priors_mat.csv"
    clr_file = "clr_matrix.csv"
    script_file = "run_bbsr.R"
    betas_file='betas.tsv'
    betas_resc_file='betas_rescaled.tsv'
    n = 10
    cores = 10
    no_prior_weight = 1
    prior_weight = 1

    def run(self, X_data_frame, Y_dataframe, clr_dataframe, priors_dataframe):
        X = utils.convert_to_R_df(X_data_frame)
        Y = utils.convert_to_R_df(Y_dataframe)
        clr = utils.convert_to_R_df(clr_dataframe)
        priors = utils.convert_to_R_df(priors_dataframe)
        X.to_csv(self.path(self.X_file), na_rep='NA')
        Y.to_csv(self.path(self.Y_file), na_rep='NA')
        clr.to_csv(self.path(self.clr_file), na_rep='NA')
        priors.to_csv(self.path(self.priors_file), na_rep='NA')
        (driver_path, design_path, response_path) = save_R_driver(
            to_filename=self.path(self.script_file),
            cores=self.cores,
            n=self.n,
            no_prior_weight=self.no_prior_weight,
            prior_weight=self.prior_weight,
            betas_file=self.path(self.betas_file),
            betas_resc_file=self.path(self.betas_resc_file),
            clr_file=self.path(self.clr_file),
            priors_file=self.path(self.priors_file),
            X_file=self.path(self.X_file),
            Y_file=self.path(self.Y_file)
        )
        utils.call_R(driver_path)
        final_design = pd.read_csv(design_path, sep='\t')
        final_response = pd.read_csv(response_path, sep='\t')
        return (final_design, final_response)

