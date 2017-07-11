## About

Grey Theory System that means uncertain relationships between the various factors within the system, this system in which part of information is known and another part is unknown. This theory has 3 methods are : GM0N, GM1N, GM11.

[Grey Relational Analysis](https://en.wikipedia.org/wiki/Grey_relational_analysis) <br />
[灰色系統理論](http://wiki.mbalib.com/zh-tw/%E7%81%B0%E8%89%B2%E7%B3%BB%E7%BB%9F%E7%90%86%E8%AE%BA) <br />
[灰色關聯分析](http://wiki.mbalib.com/zh-tw/%E7%81%B0%E8%89%B2%E5%85%B3%E8%81%94%E5%88%86%E6%9E%90) <br />
[灰色預測法](http://wiki.mbalib.com/zh-tw/%E7%81%B0%E8%89%B2%E9%A2%84%E6%B5%8B%E6%B3%95) <br />
[《Grey system theory-based models in time series prediction》2009.](http://www.mecha.ee.boun.edu.tr/Prof.%20Dr.%20Okyay%20Kaynak%20Publications/c%20Journal%20Papers(appearing%20in%20SCI%20or%20SCIE%20or%20CompuMath)/62.pdf) <br />
[改良式 GM(1,1)灰預測模型於台電電量需求預測之研究](http://www.engh.kuas.edu.tw/files/ne/pnz67gteh2.pdf)

## How To Get Started

#### Import
``` python
from grey_theory import GreyTheory
grey = GreyTheory()
```

#### GM0N
``` python

gm0n = grey.gm0n

gm0n.add_outputs([1., 1., 1., 1., 1., 1.], "x1")
gm0n.add_patterns([.75, 1.22, .2, 1., 1., 1.], "x2")
gm0n.add_patterns([.5, 1., .7, .66, 1., .5], "x3")
gm0n.add_patterns([1., 1.09, .4, .33, .66, .25], "x4")
gm0n.add_patterns([.25, .99, 1., .66, .33, .25], "x5")

gm0n.analyze()

# Looks GM0N the results as below:
gm0n.print_analyzed_results()
"""
Pattern key: 'x3', grey value: 0.745169986457907, ranking: 1
Pattern key: 'x4', grey value: 0.5714064714568454, ranking: 2
Pattern key: 'x2', grey value: 0.501334367966725, ranking: 3
Pattern key: 'x5', grey value: 0.49555636151070015, ranking: 4
"""

gm0n.print_influence_degrees()
"""
The keys of parameters their influence degrees (ordering): 'x3 > x4 > x2 > x5'
"""
```

#### GM1N
``` python
gm1n = grey.gm1n

gm1n.add_outputs([2., 11., 1.5, 2., 2.2, 3.], "x1")
gm1n.add_patterns([3., 13.5, 1., 3., 3., 4.], "x2")
gm1n.add_patterns([2., 11., 3.5, 2., 3., 2.], "x3")
gm1n.add_patterns([4., 12., 2., 1., 2., 1.], "x4")
gm1n.add_patterns([1., 10., 5., 2., 1., 1.], "x5")

gm1n.analyze()

# Looks GM1N the results as below:
gm1n.print_analyzed_results()
"""
Pattern key: 'x1', grey value: 1.4385641363407546, ranking: 0
Pattern key: 'x2', grey value: 1.3300049398977922, ranking: 1
Pattern key: 'x4', grey value: 0.6084241725675539, ranking: 2
Pattern key: 'x3', grey value: 0.5977013008400084, ranking: 3
Pattern key: 'x5', grey value: 0.19277457599259723, ranking: 4
"""

gm1n.print_influence_degrees()
"""
The keys of parameters their influence degrees (ordering): 'x2 > x4 > x3 > x5'
"""
```

#### GM11
``` python
gm11 = grey.gm11

gm11.add_pattern(223.3, "a1")
gm11.add_pattern(227.3, "a2")
gm11.add_pattern(230.5, "a3")
gm11.add_pattern(238.1, "a4")
gm11.add_pattern(242.9, "a5")
gm11.add_pattern(251.1, "a6")

gm11.forecast(5) # Default is 1, the parameter means how many next moments need to forcast continually.

# Looks GM11 the results for example as below:
gm11.print_forecasted_results()
"""
K = 1
From original value 227.3 to forecasted value is 226.08736263692822
The error rate is 0.005334964201811667
K = 2
From original value 230.5 to forecasted value is 231.87637984134398
The error rate is 0.005971279138151739
K = 3
From original value 238.1 to forecasted value is 237.81362611881437
The error rate is 0.0012027462460547044
K = 4
From original value 242.9 to forecasted value is 243.9028969077225
The error rate is 0.00412884688234865
K = 5
From original value 251.1 to forecasted value is 250.14808482949547
The error rate is 0.003790980368397134
K = 6
Forcated next moment value is 256.55318217699795
K = 7
Forcated next moment value is 263.1222834666411
K = 8
Forcated next moment value is 269.85958805583954
K = 9
Forcated next moment value is 276.76940282748853
K = 10
Forcated next moment value is 283.85614494317775
The average error rate 0.0040857633673527785
"""
```

#### GM11 Convolutional Forecasting
``` python
# Convolutional forecasting of GM11, forecast_convolution(stride, length)
gm11.forecast_convolution(1, 4) 

# To record last forecasted result.
last_forecasted_results = gm11.forecasted_outputs

# To clean all forecasted results. 
gm11.clean_forecasted()

# In next iteration of forecasting, we wanna continue use last forecasted results to do next forecasting, 
# but if we removed gm11.forecasted_outputs list before,  
# we can use continue_forecasting() to extend / recall the last forecasted result come back to be convolutional features. 
gm11.continue_forecasting(last_forecasted_results)
```

#### Alpha for Z
``` python
# For example, if you wanna customize alpha value to reduce error-rate of prediction before calculate AGO, 
# Directly try to setup the alpha value before start .analyze() and .forecast().
gm11.alpha = 0.8
gm11.add_pattern() 
gm11.forecast()
```

## Version

V1.2

## LICENSE

MIT.

## Note

卷積的部份，是跑 2 層的 GM11:
1 -> 2 -> 3, 預測 4 
2 -> 3 -> 4, 預測 5
3 -> 4 -> 5, 預測 6
... 其餘類推

之後會把預測 4，5，6 再丟進去 GM11 跑最終結果。等於是先做一次特徵提取，第 1 層提取每一個區間的預測輸出，再對這預測輸出做平均誤差的修正，而後再丟入第 2 層的 GM11 去做總輸出。
