
def custom_round(val:float, min_dec: int = 2):
    """
    Return rounded value with auto adjustable decimal places in order to not display 0
    Args:
        val(float):
            Value you want to round

        min_dec(int, optional):
            Minimum decimal places to round.
    
    Returns:
        float: 
            Rounded number.
    """
    temp = abs(val)
    count_round = min_dec
    while temp < 1 and temp > 0:
        temp = temp*10
        count_round +=1  
    return round(val, count_round)