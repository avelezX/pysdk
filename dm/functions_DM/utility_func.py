

#fuctions for data frames
# Function to check if a column name contains 'Date', 'date', 'time', or 'Time'
def columns_with_date(df):

    def check_column_name(name):
        return 'Date' in name or 'date' in name or 'time' in name or 'Time' in name

    # Identify columns meeting the condition
    return [col for col in df if check_column_name(col)]

def fit_nelson_siegel(x, y):
    def nelson_siegel_curve(t, beta0, beta1, beta2, tau):
        return beta0 + beta1 * ((1 - np.exp(-t / tau)) / (t / tau)) + beta2 * (((1 - np.exp(-t / tau)) / (t / tau)) - np.exp(-t / tau))

