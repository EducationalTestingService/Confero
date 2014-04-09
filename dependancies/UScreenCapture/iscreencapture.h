
#pragma once

// {C218F4B9-18AA-42fa-AAB0-1AF5C56D1C74}
DEFINE_GUID(IID_IUScreenCaptureSettings2, 
0xc218f4b9, 0x18aa, 0x42fa, 0xaa, 0xb0, 0x1a, 0xf5, 0xc5, 0x6d, 0x1c, 0x74);


DECLARE_INTERFACE_(IUScreenCaptureSettings2, IUnknown) {

    STDMETHOD(get_Region) (THIS_
                int * pnLeftTopX, int * pnLeftTopY, 
				int * pnRightBottomX, int * pnRightBottomY        /* [out] */    // the current size
             ) PURE;

    STDMETHOD(put_Region) (THIS_
                int nLeftTopX, int nLeftTopY, 
				int nRightBottomX, int nRightBottomY 			  /* [in] */     // Change to this size
             ) PURE;

    STDMETHOD(get_FramesPerSec) (THIS_
                 int * pnFramesPerSec			/* [out] */   // the current FrameRate
             ) PURE;                                          // Valid range: 1-30

    STDMETHOD(put_FramesPerSec) (THIS_
                  int  nFramesPerSec			/* [in] */    // Change to this FrameRate
             ) PURE;                                          // Valid range: 1-30

    STDMETHOD(get_MonitorNumber) (THIS_
                 int * pnMonitorNumber			/* [out] */   // the current nMonitorNumber
             ) PURE;                                          // Valid range: 1-2

    STDMETHOD(put_MonitorNumber) (THIS_
                  int  nMonitorNumber	        /* [in] */    // Change to this nMonitorNumber
             ) PURE;                                          // Valid range: 1-2

    STDMETHOD(get_ShowCursor) (THIS_
                  BOOL* bShowCursor 	        /* [out] */   // Returns current ShowCursor option
             ) PURE;

    STDMETHOD(put_ShowCursor) (THIS_
                  BOOL bShowCursor 	            /* [in] */    // Changes current ShowCursor option
             ) PURE;

    STDMETHOD(get_CaptureLayeredWindows) (THIS_
                  BOOL* bCapture 	            /* [out] */   // Returns current CaptureLayeredWindows option
             ) PURE;

    STDMETHOD(put_CaptureLayeredWindows) (THIS_
                  BOOL bCapture 	            /* [in] */    // Changes current CaptureLayeredWindows option
             ) PURE;

};



