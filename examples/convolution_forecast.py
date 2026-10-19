"""Compare ordinary GM11 with the two-level convolution forecast."""

from greytheory import GM11


def main():
    series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
    ordinary = GM11(background_mode="corrected").fit(series)
    convolution = GM11(
        background_mode="corrected", window_size=4, stride=1,
    ).fit(series)
    print("Input:", series)
    print("Ordinary GM11, next two values:", ordinary.predict(2).round(4).tolist())
    print("Convolution GM11, next two values:", convolution.predict(2).round(4).tolist())
    print("Window size:", convolution.window_size, "stride:", convolution.stride)
    print("Window predictions and final second-level result:",
          [round(value, 4) for value in convolution.forecasted_outputs])


if __name__ == "__main__":
    main()
