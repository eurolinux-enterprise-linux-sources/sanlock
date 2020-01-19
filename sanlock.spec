%define with_systemd 0%{!?_without_systemd:0}

%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
%define with_systemd 1
%endif

Name:           sanlock
Version:        3.5.0
Release:        1%{?dist}
Summary:        A shared storage lock manager

Group:          System Environment/Base
License:        GPLv2 and GPLv2+ and LGPLv2+
URL:            https://fedorahosted.org/sanlock/
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:  libblkid-devel libaio-devel python python-devel
ExclusiveArch:  x86_64 aarch64 s390x %{power64}
%if %{with_systemd}
BuildRequires:  systemd-units
%endif
Requires:       %{name}-lib = %{version}-%{release}
Requires(pre):  /usr/sbin/groupadd
Requires(pre):  /usr/sbin/useradd
%if %{with_systemd}
Requires(post): systemd-units
Requires(post): systemd-sysv
Requires(preun): systemd-units
Requires(postun): systemd-units
%endif
Source0:        https://releases.pagure.org/sanlock/%{name}-%{version}.tar.gz

# Patch0: 0001-foo.patch

%description
The sanlock daemon manages leases for applications on hosts using shared storage.

%prep
%setup -q
# %patch0 -p1 -b .0001-foo.patch

%build
# upstream does not require configure
# upstream does not support _smp_mflags
CFLAGS=$RPM_OPT_FLAGS make -C wdmd
CFLAGS=$RPM_OPT_FLAGS make -C src
CFLAGS=$RPM_OPT_FLAGS make -C python
CFLAGS=$RPM_OPT_FLAGS make -C fence_sanlock
CFLAGS=$RPM_OPT_FLAGS make -C reset

%install
rm -rf $RPM_BUILD_ROOT
make -C src \
        install LIBDIR=%{_libdir} \
        DESTDIR=$RPM_BUILD_ROOT
make -C wdmd \
        install LIBDIR=%{_libdir} \
        DESTDIR=$RPM_BUILD_ROOT
make -C python \
        install LIBDIR=%{_libdir} \
        DESTDIR=$RPM_BUILD_ROOT
make -C fence_sanlock \
        install LIBDIR=%{_libdir} \
        DESTDIR=$RPM_BUILD_ROOT
make -C reset \
        install LIBDIR=%{_libdir} \
        DESTDIR=$RPM_BUILD_ROOT


%if %{with_systemd}
install -D -m 0644 init.d/sanlock.service.native $RPM_BUILD_ROOT/%{_unitdir}/sanlock.service
install -D -m 0755 init.d/wdmd $RPM_BUILD_ROOT/usr/lib/systemd/systemd-wdmd
install -D -m 0644 init.d/wdmd.service.native $RPM_BUILD_ROOT/%{_unitdir}/wdmd.service
install -D -m 0755 init.d/fence_sanlockd $RPM_BUILD_ROOT/usr/lib/systemd/systemd-fence_sanlockd
install -D -m 0644 init.d/fence_sanlockd.service $RPM_BUILD_ROOT/%{_unitdir}/fence_sanlockd.service
install -D -m 0644 init.d/sanlk-resetd.service $RPM_BUILD_ROOT/%{_unitdir}/sanlk-resetd.service
%else
install -D -m 0755 init.d/sanlock $RPM_BUILD_ROOT/%{_initddir}/sanlock
install -D -m 0755 init.d/wdmd $RPM_BUILD_ROOT/%{_initddir}/wdmd
install -D -m 0755 init.d/fence_sanlockd $RPM_BUILD_ROOT/%{_initddir}/fence_sanlockd
%endif

install -D -m 0644 src/logrotate.sanlock \
	$RPM_BUILD_ROOT/etc/logrotate.d/sanlock

install -D -m 0644 src/sanlock.conf \
	$RPM_BUILD_ROOT/etc/sanlock/sanlock.conf

install -D -m 0644 init.d/wdmd.sysconfig \
	$RPM_BUILD_ROOT/etc/sysconfig/wdmd

install -Dd -m 0755 $RPM_BUILD_ROOT/etc/wdmd.d
install -Dd -m 0775 $RPM_BUILD_ROOT/%{_localstatedir}/run/sanlock
install -Dd -m 0775 $RPM_BUILD_ROOT/%{_localstatedir}/run/fence_sanlock
install -Dd -m 0775 $RPM_BUILD_ROOT/%{_localstatedir}/run/fence_sanlockd
install -Dd -m 0775 $RPM_BUILD_ROOT/%{_localstatedir}/run/sanlk-resetd

%clean
rm -rf $RPM_BUILD_ROOT

%pre
getent group sanlock > /dev/null || /usr/sbin/groupadd \
	-g 179 sanlock
getent passwd sanlock > /dev/null || /usr/sbin/useradd \
	-u 179 -c "sanlock" -s /sbin/nologin -r \
	-g 179 -d /var/run/sanlock sanlock
/usr/sbin/usermod -a -G disk sanlock

%post
%if %{with_systemd}
%systemd_post wdmd.service sanlock.service
%endif

%preun
%if %{with_systemd}
%systemd_preun wdmd.service sanlock.service
%endif

%postun
%if %{with_systemd}
%systemd_postun
%endif

%files
%defattr(-,root,root,-)
%if %{with_systemd}
/usr/lib/systemd/systemd-wdmd
%{_unitdir}/sanlock.service
%{_unitdir}/wdmd.service
%else
%{_initddir}/sanlock
%{_initddir}/wdmd
%endif
%{_sbindir}/sanlock
%{_sbindir}/wdmd
%dir %{_sysconfdir}/wdmd.d
%dir %{_sysconfdir}/sanlock
%dir %attr(-,sanlock,sanlock) %{_localstatedir}/run/sanlock
%{_mandir}/man8/wdmd*
%{_mandir}/man8/sanlock*
%config(noreplace) %{_sysconfdir}/logrotate.d/sanlock
%config(noreplace) %{_sysconfdir}/sanlock/sanlock.conf
%config(noreplace) %{_sysconfdir}/sysconfig/wdmd
%doc init.d/sanlock
%doc init.d/sanlock.service
%doc init.d/wdmd.service

%package        lib
Summary:        A shared storage lock manager library
Group:          System Environment/Libraries

%description    lib
The %{name}-lib package contains the runtime libraries for sanlock,
a shared storage lock manager.
Hosts connected to a common SAN can use this to synchronize their
access to the shared disks.

%post lib -p /sbin/ldconfig

%postun lib -p /sbin/ldconfig

%files          lib
%defattr(-,root,root,-)
%{_libdir}/libsanlock.so.*
%{_libdir}/libsanlock_client.so.*
%{_libdir}/libwdmd.so.*

%package        python
Summary:        Python bindings for the sanlock library
Group:          Development/Libraries
Requires:       %{name}-lib = %{version}-%{release}

%description    python
The %{name}-python package contains a module that permits applications
written in the Python programming language to use the interface
supplied by the sanlock library.

%files          python
%defattr(-,root,root,-)
%{python_sitearch}/sanlock_python-*.egg-info
%{python_sitearch}/sanlock.so

%package        devel
Summary:        Development files for %{name}
Group:          Development/Libraries
Requires:       %{name}-lib = %{version}-%{release}

%description    devel
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.

%files          devel
%defattr(-,root,root,-)
%{_libdir}/libwdmd.so
%{_includedir}/wdmd.h
%{_libdir}/libsanlock.so
%{_libdir}/libsanlock_client.so
%{_includedir}/sanlock.h
%{_includedir}/sanlock_rv.h
%{_includedir}/sanlock_admin.h
%{_includedir}/sanlock_resource.h
%{_includedir}/sanlock_direct.h
%{_libdir}/pkgconfig/libsanlock.pc
%{_libdir}/pkgconfig/libsanlock_client.pc

%package -n     fence-sanlock
Summary:        Fence agent using sanlock and wdmd
Group:          System Environment/Base
Requires:       sanlock = %{version}-%{release}
Requires:       sanlock-lib = %{version}-%{release}

%description -n fence-sanlock
The fence-sanlock package contains the fence agent and
daemon for using sanlock and wdmd as a cluster fence agent.

%files -n       fence-sanlock
%defattr(-,root,root,-)
%if %{with_systemd}
/usr/lib/systemd/systemd-fence_sanlockd
%{_unitdir}/fence_sanlockd.service
%else
%{_initddir}/fence_sanlockd
%endif
%{_sbindir}/fence_sanlock
%{_sbindir}/fence_sanlockd
%dir %attr(-,root,root) %{_localstatedir}/run/fence_sanlock
%dir %attr(-,root,root) %{_localstatedir}/run/fence_sanlockd
%{_mandir}/man8/fence_sanlock*

%post -n        fence-sanlock
if [ $1 -eq 1 ] ; then
%if %{with_systemd}
  /bin/systemctl daemon-reload >/dev/null 2>&1 || :
%else
  /sbin/chkconfig --add fence_sanlockd
%endif
fi

%preun -n       fence-sanlock
if [ $1 = 0 ]; then
%if %{with_systemd}
  /bin/systemctl --no-reload fence_sanlockd.service > /dev/null 2>&1 || :
%else
  /sbin/service fence_sanlockd stop > /dev/null 2>&1
  /sbin/chkconfig --del fence_sanlockd
%endif
fi

%postun -n      fence-sanlock
if [ $1 -ge 1 ] ; then
%if %{with_systemd}
  /bin/systemctl try-restart fence_sanlockd.service > /dev/null 2>&1 || :
%else 
  /sbin/service fence_sanlockd condrestart >/dev/null 2>&1 || :
%endif
fi

%package -n     sanlk-reset
Summary:        Host reset daemon and client using sanlock
Group:          System Environment/Base
Requires:       sanlock = %{version}-%{release}
Requires:       sanlock-lib = %{version}-%{release}

%description -n sanlk-reset
The sanlk-reset package contains the reset daemon and client.
A cooperating host running the daemon can be reset by a host
running the client, so long as both maintain access to a
common sanlock lockspace.

%files -n       sanlk-reset
%defattr(-,root,root,-)
%{_sbindir}/sanlk-reset
%{_sbindir}/sanlk-resetd
%if %{with_systemd}
%{_unitdir}/sanlk-resetd.service
%endif
%dir %attr(-,root,root) %{_localstatedir}/run/sanlk-resetd
%{_mandir}/man8/sanlk-reset*



%changelog
* Wed Apr 26 2017 David Teigland <teigland@redhat.com> - 3.5.0-1
- Update to sanlock-3.5.0

* Fri Jun 10 2016 David Teigland <teigland@redhat.com> - 3.4.0-1
- Update to sanlock-3.4.0

* Mon Feb 22 2016 David Teigland <teigland@redhat.com> - 3.3.0-1
- Update to sanlock-3.3.0

* Tue Dec 01 2015 David Teigland <teigland@redhat.com> - 3.2.4-2
- wdmd: prevent probe while watchdog is used

* Fri Jun 19 2015 David Teigland <teigland@redhat.com> - 3.2.4-1
- Update to sanlock-3.2.4

* Fri May 22 2015 David Teigland <teigland@redhat.com> - 3.2.3-2
- add pkgconfig files

* Wed May 20 2015 David Teigland <teigland@redhat.com> - 3.2.3-1
- Update to sanlock-3.2.3

* Thu Oct 30 2014 David Teigland <teigland@redhat.com> - 3.2.2-2
- checksum endian fix

* Mon Sep 29 2014 David Teigland <teigland@redhat.com> - 3.2.2-1
- Update to sanlock-3.2.2

* Thu Aug 21 2014 David Teigland <teigland@redhat.com> - 3.2.1-1
- Update to sanlock-3.2.1

* Mon Aug 18 2014 David Teigland <teigland@redhat.com> - 3.2.0-1
- Update to sanlock-3.2.0

* Wed Jan 29 2014 David Teigland <teigland@redhat.com> - 3.1.0-2
- version interface

* Tue Jan 07 2014 David Teigland <teigland@redhat.com> - 3.1.0-1
- Update to sanlock-3.1.0

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 3.0.1-3
- Mass rebuild 2013-12-27

* Thu Aug 01 2013 David Teigland <teigland@redhat.com> - 3.0.1-2
- use /usr/lib instead of /lib

* Wed Jul 31 2013 David Teigland <teigland@redhat.com> - 3.0.1-1
- Update to sanlock-3.0.1

* Wed Jul 24 2013 David Teigland <teigland@redhat.com> - 3.0.0-1
- Update to sanlock-3.0.0

