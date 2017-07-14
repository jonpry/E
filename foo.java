/*
  Copyright 2017 The E Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package life.stel.e.test;

import life.stel.e.another;

/**
 * A multiline comment
 */

public final class TestClass {

    public static int sFoo = 2;
    public static int sBar = 3;
    public ulong mBar=4; 
    public uint mFoo=5,mBah,mBam=6;

    public static int func(int j) throws Exception {
        int i=100+j;
        return i;
    }

    public static void constant_int_test() throws Exception {
        int a = 127ub;
        int b = 128;
        int c = 32767;
        int d = 65535u;
        int e = 0xFFFFui;

        print_int(a);
        print_int(b);
        print_int(c);
        print_int(d);
        print_int(e);
    }

    public static void constant_float_test() throws Exception {
        float a = 0.111;
        float b = 2;
        float c = 0.222f;
        double d = 0.312d;
        float e = .1;
        float f = 1.;

        print_float(a);
        print_float(b);
        print_float(c);
        print_double(d);
        print_float(e);
        print_float(f);
    }

    public static void bool_interp_test() throws Exception {
        int a = 1 ? 1 : 2;
        int b = 0 ? 1 : 2;
        int c = 0.1 ? 1 : 2;
        int d = 1.0 ? 1 : 2;
        int e = 0.0 ? 1 : 2;
        int f = -1 ? 1 : 2;
        int g = -1.0 ? 1 : 2;

        print_int(a);
        print_int(b);
        print_int(c);
        print_int(d);
        print_int(e);
        print_int(f);
        print_int(g);
    }

    public static void block_test() throws Exception {
        int i=1;
        {
           int j=2;
           print_int(j);
        }

        {
           int j=3;
           print_int(j);
        }

        print_int(i);
    }

    public static void if_test(boolean c) throws Exception {
        int i=0;
        int j=0;
        if(c){
            i=1;
        }else{
            i=2;
        }
        if(c){
            j = 2;
        }

        print_int(i);
        print_int(j);
    }

    public static void for_test(int k) throws Exception {
        int i=0;
        int j=0;
        for(i=0; i < k; i++){
           j = i + 2;
           if(i % 10 == 7)
             break;
        }
        print_int(j);
    }

    public static void multiple_parm_test(int i, int j){
        int f = i + j;
        print_int(f);
    }

    public static int main() throws Exception {
        constant_int_test();
        constant_float_test();
        bool_interp_test();
        block_test();
        if_test(true);
        for_test(10);
        multiple_parm_test(1,2);

        float r=1;
        r += 1;
        int i=0;
        long v=100l;
        boolean f=false;	
        f = f || true && true || ~false;
        i = f ? i - 2 + 3 * 2 / 2 % 3 << 1 >> 1 ^ 4 | 2 & 2 + (3 * 2) << 1 >>> 1: 0;
        i = i + 0x10;
        f = i > 100;
        f = i++ != 120;
        i += func(2);
        i -= (short)1;
        i |= 3;
        i <<= 2;
        i >>= 1;
        i >>>= 1;
        i *= 1;
        i /= 1;
        i %= 1000;
        i &= 0xFFFFF;
        i ^= 1;
        i += sFoo;
        i += (int)1.0;
        print_int(i);
        return i;
    }
}

