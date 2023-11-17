srcdir  = src
objdir  = .build
bindir  = bin
testdir = test

cc     	= gcc
cflags  = -g -std=c11 -pedantic -Wall -Wextra -Wno-unused-parameter

target  = $(bindir)/main
src     = $(wildcard $(srcdir)/*.c)
obj     = $(patsubst $(srcdir)/%.c,$(objdir)/%.o,$(src))


all: $(target)

$(target): $(obj)
	$(cc) $(cflags) -lm $^ -o $@


$(objdir)/%.o: $(srcdir)/%.c
	$(cc) $(cflags) -c $< -o $@


.PHONY: clean
clean:
	rm -f $(target) $(obj)
