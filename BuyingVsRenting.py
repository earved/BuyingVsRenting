import ttkbootstrap as ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

# === define functions
def main_calculator(dates, Parameters, Constants):
    debt_free_date = pd.Timestamp(int(Parameters["startyear"]),1,1) # init value
    retirement_date = pd.Timestamp(int(Parameters["startyear"] + Parameters["retirement_age"] - Parameters["age"]), 1, 1)
    date_in_15j = pd.Timestamp(int(Parameters["startyear"]) + 15, 1, 1) #15 years from today

    purchase_additional_costs = Constants["house_purchase_additional_costs_rate"] * Parameters["house_price"]  # house_price additional fees
    loan_amount = max([0,Parameters["house_price"] + purchase_additional_costs - Parameters["start_capital"] + Parameters["emergency_fund"]])

    # === changing values
    etf_interest = Parameters["etf_interest"] # lower in retirement due to conservative investment strategy
    loan_interest = Parameters["loan_interest"] # changes after 15 years since contract ends

    # === preallocation
    N = len(dates)
    loan_rate_vec =[0]*N
    net_income_vec = [0]*N
    repayment_vec = [0]*N
    interest_vec = [0]*N
    debt_vec = [0]*N
    special_repayment_vec = [0]*N
    house_value_vec = [0]*N
    portfolio_value_vec = [0]*N
    interest_gains_tax_vec= [0]*N
    housemaintenance_vec = [0]*N
    total_capital_vec = [0]*N
    rent_vec = [0]*N
    expenses_vec = [0]*N
    etf_interest_vec = [0]*N

    step=0
    retirement_switch = 0
    # === main loop
    for date in dates:
        # monthly income and expenses (increases with inflation)
        if step == 0: # initialize income
            net_income_vec[step] = Parameters["net_income"]
            expenses_vec[step] = Parameters["expenses"]
        else:
            net_income_vec[step] = net_income_vec[step-1] * (1 + Parameters["salary_increase_rate"] / 12) 
            expenses_vec[step] = expenses_vec[step-1] * (1 + Parameters["expenses_increase_rate"] / 12)

        # update income and etf interest rate in retirement 
        if (date - retirement_date).days > 0 and retirement_switch == 0:
            net_income_vec[step] = Parameters["pension"] 
            etf_interest = Parameters["etf_interest_retirement"] # smaller interest rate due to conservative investment strategy
            retirement_switch = 1

        # update loan interest rate after 15 years
        if (date - date_in_15j).days > 0:
            loan_interest = Parameters["loan_interest_15j"] 

        # debt
        if step == 0:
            debt_vec[step] = loan_amount # init value for debt
        else:
            debt_vec[step] = debt_next_step
        if debt_vec[step] == 0 and debt_vec[step-1] > 0:
            debt_free_date = date

        # loan infos
        if  debt_vec[step] > 0:
            loan_rate_vec[step] = Parameters["loan"]
        else:
            loan_rate_vec[step] = 0
        interest_vec[step]= debt_vec[step] * loan_interest / 12

        # repayment
        if debt_vec[step] == 0:
            repayment_vec[step] = 0
        else:
            repayment_vec[step] = Parameters["loan"] - interest_vec[step]

        # rent
        rent_vec[step] = (Parameters["house_price"]==0) * Parameters["rent"] * (1 + Parameters["rent_increase_rate"] / 12) ** step

        #ETF portfolio
        if step == 0:
            portfolio_value_vec[step] = (Parameters["house_price"]==0) * (Parameters["start_capital"] - Parameters["emergency_fund"]) 
            # zero in house buying scenario since all money is used for house
            house_value_vec[step] = Parameters["house_price"]
        else:
            etf_portfolio_increase = net_income_vec[step] - expenses_vec[step] - loan_rate_vec[step] - rent_vec[step]
            portfolio_value_vec[step] = portfolio_value_vec[step-1] + etf_portfolio_increase
            house_value_vec[step] = house_value_vec[step-1] * (1 + Parameters["house_price_increase_rate"] / 12)

        # House
        housemaintenance_vec[step] = Parameters["housemaintenance_rate"] / 12 * house_value_vec[step]

        # interests & tax correction of etf
        etf_interest_vec[step] = portfolio_value_vec[step] * etf_interest / 12
        interest_gains_tax_vec[step]= max(etf_interest_vec[step]-Constants["YearlyTaxFreeInterests"]/12, 0) * Constants["ETF_tax_rate"]
        portfolio_value_vec[step]= portfolio_value_vec[step]+etf_interest_vec[step]-interest_gains_tax_vec[step]-housemaintenance_vec[step] # correction of portfolie value after interests and taxes

        # special repayments of loan at the end of each year if possible
        if date.month == 12 and portfolio_value_vec[step]>Parameters["emergency_fund"]+Parameters["special_repayment"] and debt_vec[step]>(Parameters["special_repayment"]+repayment_vec[step]):
            special_repayment_vec[step] = Parameters["special_repayment"]
            portfolio_value_vec[step] = portfolio_value_vec[step] - Parameters["special_repayment"]
            debt_next_step = max(debt_vec[step] - repayment_vec[step] - Parameters["special_repayment"], 0)
        else:
            # update debt of next cycle
            if debt_vec[step] - repayment_vec[step] > 0:
                debt_next_step = debt_vec[step] - repayment_vec[step]
            elif debt_vec[step]>0: 
                portfolio_value_vec[step] = portfolio_value_vec[step] + repayment_vec[step] - debt_vec[step]
                repayment_vec[step] = debt_vec[step]
                debt_next_step = 0
            else:
                repayment_vec[step] = 0
                debt_next_step = 0
            special_repayment_vec[step] = 0


        # calculate total value
        total_capital_vec[step] = Parameters["emergency_fund"] + portfolio_value_vec[step] - debt_vec[step] + house_value_vec[step]

        # increment step
        step += 1

        #update progress bar
        if round(step/N*100) % 5 == 0:
            progressbar["value"]=step/N*100
            root.update_idletasks() # Update the GUI

    # output scenario results as dataframe
    df = pd.DataFrame({
        "debt_vec": debt_vec,
        "total_capital_vec": total_capital_vec,
        "portfolio_value_vec": portfolio_value_vec,
        "loan_rate_vec": loan_rate_vec,
        "net_income_vec": net_income_vec,
        "expenses_vec": expenses_vec,
        "repayment_vec": repayment_vec,
        "interest_vec": interest_vec,
        "special_repayment_vec": special_repayment_vec,
        "house_value_vec": house_value_vec,
        "interest_gains_tax_vec": interest_gains_tax_vec,
        "housemaintenance_vec": housemaintenance_vec,
        "rent_vec": rent_vec,
        "etf_interest_vec": etf_interest_vec
    }, index=dates)

    #print(sum(repayment_vec)+sum(special_repayment_vec)) equals initial debt

    key_values = { #unit k€
        "house_purchase_additional_costs" : Constants["house_purchase_additional_costs_rate"]*Parameters["house_price"]/1000,
        "housemaintenance" : sum(housemaintenance_vec)/1000,
        "total_etf_interests" : sum(etf_interest_vec)/1000,
        "total_income" : sum(net_income_vec)/1000,
        "total_expenses": sum(expenses_vec)/1000, 
        "total_interests" : sum(interest_vec)/1000,
        "house_value_gain" : (house_value_vec[-1]-house_value_vec[0])/1000,
        "total_interest_gain_tax" : sum(interest_gains_tax_vec)/1000,
        "total_rent" : sum(rent_vec)/1000
    }

    return df, key_values, debt_free_date, retirement_date

def calc_and_plot_scenario():
    """ get defaults, overwrite with user entries, convert units and create plots """
    Parameters, ParameterLabelTexts, Constants = get_defaults()
    cnt = 0
    for key in Parameters.keys():
        try:
            Parameters[key] = float(VariableEntries[cnt].get())
            cnt += 1
        except:
            VariableEntries[cnt].delete(0,'end')
            VariableEntries[cnt].insert(0,"nur Zahlen erlaubt!")
            return

    # unit conversion
    Parameters["house_price"] = Parameters["house_price"] * 1000 #k€ to €
    Parameters["start_capital"] = Parameters["start_capital"] * 1000 #k€ to €
    Parameters["emergency_fund"] = Parameters["emergency_fund"] * 1000 #k€ to €
    Parameters["salary_increase_rate"] = Parameters["salary_increase_rate"] / 100 # convert to [0,1]
    Parameters["expenses_increase_rate"] = Parameters["expenses_increase_rate"] / 100 # convert to [0,1]
    Parameters["loan_interest"] = Parameters["loan_interest"] / 100 # convert to [0,1]
    Parameters["loan_interest_15j"] = Parameters["loan_interest_15j"] / 100 # convert to [0,1]
    Parameters["etf_interest"] = Parameters["etf_interest"] / 100 # convert to [0,1]
    Parameters["etf_interest_retirement"] = Parameters["etf_interest_retirement"] / 100 # convert to [0,1]
    Parameters["rent_increase_rate"] = Parameters["rent_increase_rate"] / 100 # convert to [0,1]
    Parameters["house_price_increase_rate"] = Parameters["house_price_increase_rate"] / 100 # convert to [0,1]
    Parameters["housemaintenance_rate"] = Parameters["housemaintenance_rate"] / 100 # convert to [0,1]

    # set simulation time horizon
    N_years = Parameters["retirement_age"] - Parameters["age"] + Constants["years_after_retirement"]
    startdate = pd.Timestamp(int(Parameters["startyear"]), 1, 1)
    dates = pd.date_range(start=startdate, periods=int(N_years * 12 - 1), freq='MS')

    # calculate buying scenario 
    progressbarlabel.config(text = "Berechne Kaufszenario...")
    df_buy, key_values_buy, debt_free_date, retirement_date = main_calculator(dates, Parameters, Constants)

    # ouput calculations of buying scenario
    labeltext = "Eigenkapitalquote: " + str(round(100*Parameters["start_capital"]/(Parameters["house_price"]*(1+Constants["house_purchase_additional_costs_rate"])),1)) +" %"
    labeltext = labeltext + "\n" + "Anfängliche Tilgung: "+ str(round(df_buy["repayment_vec"].iloc[0]/df_buy["debt_vec"].iloc[0]*12*100,2)) + " %"
    labeltext = labeltext + "\n" + " "
    labeltext = labeltext + "\n" + "Bilanz:"
    labeltext = labeltext + "\n" + "+ Startkapital: " + str(round(Parameters["start_capital"]/1000))  + " k€"
    labeltext = labeltext + "\n" + "+ Einkommen ges.: " + str(round(key_values_buy["total_income"])) + " k€"
    labeltext = labeltext + "\n" + "+ Hauswertsteigerung: " + str(round(key_values_buy["house_value_gain"]))+" k€"
    labeltext = labeltext + "\n" + "+ Kapitalerträge ges.: " + str(round(key_values_buy["total_etf_interests"])) + " k€"
    labeltext = labeltext + "\n" + "- Kaufnebenkosten: " + str(round(key_values_buy["house_purchase_additional_costs"])) + " k€"
    labeltext = labeltext + "\n" + "- Kreditzinsen ges.: " + str(round(key_values_buy["total_interests"])) +" k€"
    labeltext = labeltext + "\n" + "- Instandhaltung & Grundsteuer ges.: " + str(round(key_values_buy["housemaintenance"])) + " k€"
    labeltext = labeltext + "\n" + "- Kapitalertragssteuer ges.: " + str(round(key_values_buy["total_interest_gain_tax"])) + " k€"
    labeltext = labeltext + "\n" + "- Ausgaben ges.:: " + str(round(key_values_buy["total_expenses"])) + " k€" 
    labeltext = labeltext + "\n" + "---------------------"
    labeltext = labeltext + "\n" + "~= " + str(round(df_buy["total_capital_vec"].iloc[-1]/1000)) + " k€" 
    outputlabelbuying.config(text=labeltext)

    # calculate renting scenario 
    Parameters["house_price"] = 0
    Parameters["loan"] = 0
    Parameters["special_repayment"] = 0
    progressbarlabel.config(text = "Berechne Mietszenario...")
    df_rent, key_values_rent, debt_free_date_rent, retirement_date_rent  = main_calculator(dates, Parameters, Constants)

    # ouput calculations of renting scenario
    labeltext = "Bilanz:"
    labeltext = labeltext + "\n" +"+ Startkapital: " + str(round(Parameters["start_capital"]/1000))  + " k€"
    labeltext = labeltext + "\n" + "+ Einkommen insg.: " + str(round(key_values_rent["total_income"])) + " k€"
    labeltext = labeltext + "\n" + "+ Kapitalerträge ges.: " + str(round(key_values_rent["total_etf_interests"])) + " k€"
    labeltext = labeltext + "\n" + "- Kapitalertragssteuer ges.: " + str(round(key_values_rent["total_interest_gain_tax"])) + " k€"
    labeltext = labeltext + "\n" + "- Miete ges.: " + str(round(key_values_rent["total_rent"])) + " k€"   
    labeltext = labeltext + "\n" + "- Ausgaben ges.:: " + str(round(key_values_rent["total_expenses"])) + " k€" 
    labeltext = labeltext + "\n" + "---------------------"
    labeltext = labeltext + "\n" + "~= " + str(round(df_rent["total_capital_vec"].iloc[-1]/1000)) + " k€" 
    outputlabelrenting.config(text=labeltext)

    # plotting
    fig = plt.figure(figsize=(8,8))
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212)

    # first plot
    ax1.plot(df_buy.index, df_buy["total_capital_vec"] / 1000, color='b', label="Vermögen Kaufen")
    ax1.plot(df_buy.index, df_buy["debt_vec"] / 1000, color='b', linestyle="dashed", label="Kreditschulden")
    ax1.plot(startdate,df_buy["debt_vec"].iloc[0] / 1000,'or')
    ax1.plot(df_buy.index, df_buy["portfolio_value_vec"] / 1000 + Parameters["emergency_fund"] / 1000, \
            color='b', linestyle=":", label="liquides Vermögen")  
    ax1.plot(df_buy.index,df_buy["house_value_vec"]/1000, color='b', linewidth=1.0,  linestyle="-.", label="Hauswert")
    ax1.plot(df_rent.index, df_rent["total_capital_vec"] / 1000, label="Vermögen Mieten", color="k", linestyle="dashdot")
    ax1.plot(debt_free_date,0,'og')

    ax1.text(df_buy.index[0], df_buy["debt_vec"].iloc[0] / 1000, f"{int(-df_buy["debt_vec"].iloc[0]/1000)} k€")
    ax1.text(df_buy.index[0],round(df_buy["portfolio_value_vec"].iloc[0]/1000),str(int(Parameters["emergency_fund"]/1000))+" k€")
    ax1.text(debt_free_date,0,str(debt_free_date.year))
    ax1.text(retirement_date,df_buy.loc[retirement_date,"total_capital_vec"]/1000, str(round(df_buy.loc[retirement_date,"total_capital_vec"]/1000))+" k€", color = 'b')
    ax1.text(retirement_date,df_buy.loc[retirement_date,"portfolio_value_vec"]/1000 + Parameters["emergency_fund"]/1000,\
              str(round(df_buy.loc[retirement_date,"portfolio_value_vec"]/1000+ Parameters["emergency_fund"]/1000))+" k€", color = 'b')
    ax1.text(retirement_date,df_rent.loc[retirement_date,"total_capital_vec"]/1000, str(round(df_rent.loc[retirement_date,"total_capital_vec"]/1000))+" k€")
    ax1.text(dates[-1],df_rent["total_capital_vec"].iloc[-1]/1000,str(round(df_rent["total_capital_vec"].iloc[-1]/1000))+ " k€")
    ax1.text(dates[-1],df_buy["total_capital_vec"].iloc[-1]/1000,str(round(df_buy["total_capital_vec"].iloc[-1]/1000))+ " k€", color = 'b')

    # plot cutting points
    cut_date = search_zero(df_rent["total_capital_vec"]-df_buy["total_capital_vec"])
    if cut_date!=0:
        ax1.plot(cut_date, df_buy.loc[cut_date,"total_capital_vec"]/1000, "og")
        ax1.text(cut_date, df_buy.loc[cut_date,"total_capital_vec"]/1000, str(cut_date.year))
    buy_zero_date = search_zero(df_buy["portfolio_value_vec"]+Parameters["emergency_fund"])
    if buy_zero_date!=0:
        ax1.plot(buy_zero_date, 0, "or")
        ax1.text(buy_zero_date, 0, str(buy_zero_date.year))
    rent_zero_date = search_zero(df_rent["total_capital_vec"])
    if rent_zero_date!=0:
        ax1.plot(rent_zero_date, 0, "or")
        ax1.text(rent_zero_date, 0, str(rent_zero_date.year))

    ax1.grid()
    ax1.set_ylabel("Vermögen in k€")
    ax1.legend()

    # second plot
    ax2.plot(df_buy.index, df_buy["repayment_vec"], label="Tilgung")
    ax2.plot(df_buy.index, df_buy["interest_vec"], label="Zinsen")
    ax2.plot(df_buy.index, df_buy["loan_rate_vec"], label="Annuität")
    ax2.plot(df_buy.index, df_buy["net_income_vec"], label="Netto Einkommen")
    ax2.plot(df_buy.index, df_buy["special_repayment_vec"], label="Sondertilgung", linestyle = 'dotted')
    ax2.plot(df_buy.index, df_buy["housemaintenance_vec"], label="Instandhaltung & Grundsteuer")
    ax2.plot(df_buy.index, df_buy["interest_gains_tax_vec"], label="Kap. Ertragssteuer (Kaufen)")
    ax2.plot(df_buy.index, df_buy["expenses_vec"], label="Ausgaben")
    ax2.plot(df_rent.index, df_rent["rent_vec"], label="Miete")
    ax2.plot(df_buy.index, df_rent["interest_gains_tax_vec"], label="Kap. Ertragssteuer (Mieten)")

    ax2.grid()
    ax2.set_xlabel("Jahr")
    ax2.set_ylabel("€ Monatlich")
    ax2.legend(loc='upper right')

    fig.tight_layout()

    progressbarlabel.config(text="Berechnung fertig!")

    # Add the plot to the plot frame
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().grid(row=1, column=0, sticky="NSEW")

def get_defaults():

    # parameters set by user
    Parameters = {   
        "age": 35,
        "startyear":2025,
        "retirement_age" : 67,
        "start_capital" : 150, #in k€
        "house_price" : 400, #k€
        "house_price_increase_rate" : 1,
        "emergency_fund" : 25, #in k€
        "net_income" : 5000, #in €
        "pension": 3500, #in €
        "expenses": 2500, #in €
        "salary_increase_rate" : 2, # % increase per year
        "expenses_increase_rate" : 2, # % increase per year
        "loan" : 2000, #in €
        "loan_interest" : 3.5,
        "loan_interest_15j" : 5,
        "etf_interest" : 5,
        "etf_interest_retirement" : 2, # smaller interest due to more conservative investment during retirement
        "housemaintenance_rate" : 0.8, # % of house value per year
        "special_repayment" : 7500, #€
        "rent" : 1400, #€
        "rent_increase_rate": 2, # % increase per year
        }
    
    ParameterLabelTexts = ["Alter","Jahr des Kaufs","Renteneintrittsalter","Eigenkapital [k€]", "Hauspreis exkl. Kaufnebenkosten [k€]",\
                           "Hauswertsteigerung p.a. [%]","Notgroschen [k€]","Monatlichs Netto [€]","Rente [€]",'Monatliche Ausgaben [€]', \
                           "Gehaltssteigerung p.a. [%]","Ausgabensteigerung (Inflation) p.a. [%]","Annuität [€]","Kreditzins p.a. [%]", \
                          "Kreditzins p.a. +15J [%]", "ETF Zins p.a. [%]","ETF Zins p.a. Rente [%]","Instandhaltung & Grundsteuer \np.a. [% vom Kaufpreis]",\
                            "Sondertilgung [€]", "Kaltmiete [€]","Mietsteigerung (Inflation) p.a. [%]"]
                              
    Constants = {
        "YearlyTaxFreeInterests" : 2000, #€
        "ETF_tax_rate" : 0.7 * 0.25,
        "house_purchase_additional_costs_rate" : 0.12,
        "years_after_retirement" : 20
    }
    return Parameters, ParameterLabelTexts, Constants

def search_zero(series):
    if len(series[series<0])>0:
        cut_date = series[series<0].index[0]
        return cut_date
    else:
        return 0

# Create the main window
root = ttk.Window(themename="flatly") # 'flatly
root.title("Kaufen vs. Mieten")

# Create a frame for the Inputs
input_frame = ttk.Frame(root, padding=10)
input_frame.grid(row=0, column=0, sticky="NSEW")

# calc button
calc_button = ttk.Button(input_frame, text="Berechne Scenario", command=calc_and_plot_scenario, bootstyle="primary")
calc_button.grid(row=0, column=1, columnspan=2, sticky="NSEW", pady = 5)

# Create a progress bar 
progressbarlabel = ttk.Label(input_frame, bootstyle="primary")
progressbarlabel.grid(row=1, column=1, sticky="NSEW")
progressbar = ttk.Progressbar(input_frame, orient="horizontal", mode='determinate', bootstyle="success") 
progressbar.grid(row=2, column=1, columnspan=2, sticky="NSEW", pady = 10)
progressbar['value'] = 0

# Add Inputs to the Input frame
Parameters, ParameterLabelTexts, Constants = get_defaults()
VariableEntries = []
gridcnt = 3
labelcnt = 0
for variable in Parameters.keys():
    label = ttk.Label(input_frame, text=ParameterLabelTexts[labelcnt], bootstyle="primary")
    label.grid(row=gridcnt, column=1, sticky="NSEW")
    labelcnt +=1

    variableEntryObject = ttk.Entry(input_frame, bootstyle="light")
    variableEntryObject.insert(0,Parameters[variable])
    variableEntryObject.grid(row=gridcnt, column=2, sticky="NSEW")
    gridcnt += 1

    VariableEntries.append(variableEntryObject)

# Create a frame for the plot
plot_frame = ttk.Frame(root, padding=10)
plot_frame.grid(row=0, column=1, sticky="NSEW")

# Create a frame for the outputs
output_frame = ttk.Frame(root, padding=10)
output_frame.grid(row=0, column=2, sticky="NSEW")

# outputs buying scenario
outputlabelframebuying= ttk.LabelFrame(output_frame, text="Berechnungen Kaufen:", bootstyle="primary")
outputlabelframebuying.grid(row=0, column=0, sticky="NSEW")
outputlabelbuying = ttk.Label(outputlabelframebuying, bootstyle="primary", anchor="w")
outputlabelbuying.pack(padx=5, pady=5, fill="both", expand=True)

# outputs renting scenario
outputlabelframerenting= ttk.LabelFrame(output_frame, text="Berechnungen Mieten:", bootstyle="primary")
outputlabelframerenting.grid(row=1, column=0, sticky="NSEW")
outputlabelrenting = ttk.Label(outputlabelframerenting, bootstyle="primary", anchor="w")
outputlabelrenting.pack(padx=5, pady=5, fill="both", expand=True)

# Configure the grid weights
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=3)
root.columnconfigure(2, weight=1)
root.rowconfigure(0, weight=1)

# run default scenario to fill GUI
calc_and_plot_scenario()

# Run the application
root.mainloop()