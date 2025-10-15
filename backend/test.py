def process(data):
    out = []
    for i in range(len(data)):
        if data[i] % 2 == 0:
            out.append(data[i] * 2)
        else:
            out.append(data[i] + 1)
    print("Done processing:", out)

process([1,2,3,4,5])
