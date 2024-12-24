import numpy as np
import matplotlib.pyplot as plt


def cost(n, m): 
    d = n - m + 1 
    if d > 0: 
        return n * (np.log2(n) + 1) / d 
    else: 
        return float('inf') 
 

def minimal_cost_gen(): 
    # The nth iteration is the length of the smallest filter  
    # for which 2**n is the optimal FFT size 
    n = 1
    m = 1 
    yield m 
    while True: 
        x = cost(n, m) 
        y = cost(n * 2, m) 
        if y < x: 
            n *= 2 
            yield m 
        m += 1 


def optimum_fft_size(filter_size):
    for n, jump in enumerate(minimal_cost_gen()):
        if jump >= filter_size:
            return 2**n


# This function is kept for scrap but is not used in the best solution
def overlap_save(y, x, H, p):
    overlap, = p.shape
    # This is silly when we're running two loops.
    # We just keep chopping up x and putting it back together.
    # Move the zero-pad out of this function, into the block function?
    xt = np.concatenate((p, x))
    yt = np.fft.ifft(np.fft.fft(xt) * H)
    y[:] = yt[overlap:]
    p[:] = x[-overlap:]
    

block_size = 440


# This works!
def fast_conv_block(y, x, H, p):
    # In this script, x and y are slices of longer arrays.
    # In an actual chain, they would not exist beyond their local size.
    N, = H.shape
    M_, = p.shape
    L = N - M_
    # This is the hurting place. These 2 lines.
    x = np.concatenate((p, x))
    p[:] = x[-len(p):]
    for t in range(0, len(x), L):
        xt = x[t:t + N]
        yt = y[t:t + L]
        if len(xt) == len(x) % L:
            xt = xt.copy()
            xt.resize(N)
        prod = np.fft.fft(xt) * H
        yt[:] = np.fft.ifft(prod)[M_:M_+len(yt)]


def fast_conv(y, x, h):
    M, = h.shape
    N = optimum_fft_size(M)

    h = h.copy()
    # I have observed that zero-padding and FFT are not commutative
    h.resize(N)
    H = np.fft.fft(h)
    p = np.zeros(shape=(M - 1,))
    
    n, = x.shape
    for t in range(0, n, block_size):
        fast_conv_block(y[t:t+block_size], x[t:t+block_size], H, p)
    
    
def stupid_conv(y, x, h):
    L, = y.shape
    Nx, = x.shape
    M, = h.shape
    assert L == Nx + M - 1
    yt = np.zeros(shape=(L, Nx))
    for i, xi in enumerate(x):
        yt[i:i+M, i] = h * xi
    y[:] = np.sum(yt, axis=1)


def lib_conv(y, x, h):
    y[:] = np.convolve(x, h, mode='full')


def test_stupid():
    # Replicate example from
    # https://cmtext.indiana.edu/synthesis/chapter4_convolution.php
    x = np.array([2, 4, 3, 6])
    h = np.array([1, 5, 2, 3, 4])
    expected_y = np.array([2, 14, 27, 35, 56, 37, 30, 24])

    y = np.empty(shape=expected_y.shape)
    stupid_conv(y, x, h)

    assert (y == expected_y).all()


def compare_methods(signal_size, filter_size, methods):
    (name1, f1), (name2, f2) = methods.items()
    conv_size = signal_size + filter_size - 1
    x = np.random.rand(signal_size)
    h = np.random.rand(filter_size)
    y1 = np.empty(shape=(conv_size,))
    y2 = np.empty(shape=(conv_size,))
    
    f1(y1, x, h)
    f2(y2, x, h)
    
    y1.resize(signal_size)
    y2.resize(signal_size)

    plt.ylabel(f'{name1} - {name2}')
    plt.plot(y1 - y2)
    plt.show()


if __name__ == '__main__':
    n, m = block_size * 10, 15

    if False:
        # Already confirmed that I'm using the library the way I want to
        test_stupid()
        compare_methods(n, m, {'lib': lib_conv, 'stupid': stupid_conv})

    compare_methods(n, m, {'lib': lib_conv, 'mine': fast_conv})
