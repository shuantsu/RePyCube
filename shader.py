color = y > 0 and RED or abs(y) > 0 and WHITE or BLACK

return abs(x) < 2 and abs(y) < 2 and z == 4 and BLACK or (sqrt(x**2+y**2+z**2) < extent / 1.1) and color