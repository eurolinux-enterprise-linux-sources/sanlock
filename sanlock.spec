Name:           sanlock
Version:        2.8
Release:        2%{?dist}
Summary:        A shared disk lock manager

Group:          System Environment/Base
License:        GPLv2 and GPLv2+ and LGPLv2+
URL:            https://fedorahosted.org/sanlock/
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
ExclusiveArch:  x86_64
BuildRequires:  libblkid-devel libaio-devel python python-devel
Requires:       %{name}-lib = %{version}-%{release}
Source0:        https://fedorahosted.org/releases/s/a/sanlock/%{name}-%{version}.tar.gz

Patch0: 0001-sanlock-fix-get_hosts-off-by-one.patch

%description
sanlock uses disk paxos to manage leases on shared storage.
Hosts connected to a common SAN can use this to synchronize their
access to the shared disks.

%prep
%setup -q
%patch0 -p1 -b .0001-sanlock-fix-get_hosts-off-by-one.patch

%build
# upstream does not require configure
# upstream does not support _smp_mflags
CFLAGS=$RPM_OPT_FLAGS make -C wdmd
CFLAGS=$RPM_OPT_FLAGS make -C src
CFLAGS=$RPM_OPT_FLAGS make -C python
CFLAGS=$RPM_OPT_FLAGS make -C fence_sanlock

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


%if 0%{?fedora} >= 16
install -D -m 0755 init.d/sanlock $RPM_BUILD_ROOT/lib/systemd/systemd-sanlock
install -D -m 0644 init.d/sanlock.service $RPM_BUILD_ROOT/%{_unitdir}/sanlock.service
install -D -m 0755 init.d/wdmd $RPM_BUILD_ROOT/lib/systemd/systemd-wdmd
install -D -m 0644 init.d/wdmd.service $RPM_BUILD_ROOT/%{_unitdir}/wdmd.service
install -D -m 0755 init.d/fence_sanlockd $RPM_BUILD_ROOT/lib/systemd/systemd-fence_sanlockd
install -D -m 0644 init.d/fence_sanlockd.service $RPM_BUILD_ROOT/%{_unitdir}/fence_sanlockd.service
%else
install -D -m 755 init.d/sanlock $RPM_BUILD_ROOT/%{_initddir}/sanlock
install -D -m 755 init.d/wdmd $RPM_BUILD_ROOT/%{_initddir}/wdmd
install -D -m 755 init.d/fence_sanlockd $RPM_BUILD_ROOT/%{_initddir}/fence_sanlockd
%endif

install -Dm 0644 src/logrotate.sanlock \
	$RPM_BUILD_ROOT/etc/logrotate.d/sanlock

install -Dm 0644 init.d/sanlock.sysconfig \
	$RPM_BUILD_ROOT/etc/sysconfig/sanlock

install -Dm 0644 init.d/wdmd.sysconfig \
	$RPM_BUILD_ROOT/etc/sysconfig/wdmd

install -dm 0755 $RPM_BUILD_ROOT/etc/wdmd.d

install -Dd -m 775 $RPM_BUILD_ROOT/%{_localstatedir}/run/sanlock
install -Dd -m 775 $RPM_BUILD_ROOT/%{_localstatedir}/run/fence_sanlock
install -Dd -m 775 $RPM_BUILD_ROOT/%{_localstatedir}/run/fence_sanlockd

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
if [ $1 -eq 1 ] ; then
%if 0%{?fedora} >= 16
  /bin/systemctl daemon-reload >/dev/null 2>&1 || :
%else
  /sbin/chkconfig --add sanlock
  /sbin/chkconfig --add wdmd
%endif
fi

%preun
if [ $1 = 0 ]; then
%if 0%{?fedora} >= 16
  /bin/systemctl --no-reload sanlock.service > /dev/null 2>&1 || :
  /bin/systemctl --no-reload wdmd.service > /dev/null 2>&1 || :
  /bin/systemctl stop sanlock.service > /dev/null 2>&1 || :
  /bin/systemctl stop wdmd.service > /dev/null 2>&1 || :
%else
  /sbin/service sanlock stop > /dev/null 2>&1
  /sbin/service wdmd stop > /dev/null 2>&1
  /sbin/chkconfig --del sanlock
  /sbin/chkconfig --del wdmd
%endif
fi

%postun
if [ $1 -ge 1 ] ; then
%if 0%{?fedora} >= 16
  /bin/systemctl try-restart sanlock.service >/dev/null 2>&1 || :
  /bin/systemctl try-restart wdmd.service >/dev/null 2>&1 || :
%else
  /sbin/service sanlock condrestart >/dev/null 2>&1 || :
  /sbin/service wdmd condrestart >/dev/null 2>&1 || :
%endif
fi

%files
%defattr(-,root,root,-)
%if 0%{?fedora} >= 16
/lib/systemd/systemd-sanlock
/lib/systemd/systemd-wdmd
%{_unitdir}/sanlock.service
%{_unitdir}/wdmd.service
%else
%{_initddir}/sanlock
%{_initddir}/wdmd
%endif
%{_sbindir}/sanlock
%{_sbindir}/wdmd
%dir /etc/wdmd.d
%dir %attr(-,sanlock,sanlock) %{_localstatedir}/run/sanlock
%{_mandir}/man8/wdmd*
%{_mandir}/man8/sanlock*
%config(noreplace) %{_sysconfdir}/logrotate.d/sanlock
%config(noreplace) %{_sysconfdir}/sysconfig/sanlock
%config(noreplace) %{_sysconfdir}/sysconfig/wdmd

%package        lib
Summary:        A shared disk lock manager library
Group:          System Environment/Libraries

%description    lib
The %{name}-lib package contains the runtime libraries for sanlock,
a shared disk lock manager.
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
%{python_sitearch}/Sanlock-1.0-py*.egg-info
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
%if 0%{?fedora} >= 16
/lib/systemd/systemd-fence_sanlockd
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
%if 0%{?fedora} >= 16
  /bin/systemctl daemon-reload >/dev/null 2>&1 || :
%else
  /sbin/chkconfig --add fence_sanlockd
%endif
ccs_update_schema > /dev/null 2>&1 ||:
fi

%preun -n       fence-sanlock
if [ $1 = 0 ]; then
%if 0%{?fedora} >= 16
  /bin/systemctl --no-reload fence_sanlockd.service > /dev/null 2>&1 || :
%else
  /sbin/service fence_sanlockd stop > /dev/null 2>&1
  /sbin/chkconfig --del fence_sanlockd
%endif
fi

%postun -n      fence-sanlock
if [ $1 -ge 1 ] ; then
%if 0%{?fedora} >= 16
  /bin/systemctl try-restart fence_sanlockd.service > /dev/null 2>&1 || :
%else 
  /sbin/service fence_sanlockd condrestart >/dev/null 2>&1 || :
%endif
fi

%changelog
* Fri Dec 05 2014 David Teigland <teigland@redhat.com> - 2.8-2
- Resolves: rhbz#1139373

* Fri Jul 12 2013 David Teigland <teigland@redhat.com> - 2.8-1
- Resolves: rhbz#960989 rhbz#960993 rhbz#961032 rhbz#966088

* Tue Oct 09 2012 David Teigland <teigland@redhat.com> - 2.6-1
- Resolves: rhbz#858964 rhbz#843073

* Mon Sep 24 2012 David Teigland <teigland@redhat.com> - 2.5-1
- Resolves: rhbz#826022 rhbz#830736 rhbz#830848 rhbz#831906 rhbz#832935 rhbz#840063 rhbz#841305 rhbz#843073

* Wed May 30 2012 David Teigland <teigland@redhat.com> - 2.3-1
- Update to sanlock-2.3

* Fri May 25 2012 Federico Simoncelli <fsimonce@redhat.com> 2.2-2
- Support multiple platforms in the spec file

* Mon May 07 2012 David Teigland <teigland@redhat.com> - 2.2-1
- Update to sanlock-2.2

* Thu Apr 05 2012 David Teigland <teigland@redhat.com> - 2.1-2
- Install service files instead of init files

* Wed Mar 21 2012 David Teigland <teigland@redhat.com> - 2.1-1
- Update to sanlock-2.1

* Fri Mar 02 2012 David Teigland <teigland@redhat.com> - 2.0-1
- Update to sanlock-2.0

* Tue Sep 20 2011 David Teigland <teigland@redhat.com> - 1.8-2
- fix useradd command in spec file

* Fri Sep 16 2011 Chris Feist <cfeist@redhat.com - 1.8-1
- Update to sanlock-1.8

* Fri Aug 19 2011 Dan Horák <dan[at]danny.cz> - 1.6-2
- build on all arches again

* Sun Aug 07 2011 Chris Feist <cfeist@redhat.com> - 1.7-4
- Fix for minor file include issues

* Fri Aug 05 2011 David Teigland <teigland@redhat.com> - 1.7-3
- fix man page mode

* Fri Aug 05 2011 David Teigland <teigland@redhat.com> - 1.7-1
- Update to sanlock-1.7

* Fri Jul 08 2011 David Teigland <teigland@redhat.com> - 1.6-1
- Update to sanlock-1.6

* Thu Jun 30 2011 David Teigland <teigland@redhat.com> - 1.5-1
- Update to sanlock-1.5

* Tue Jun 21 2011 David Teigland <teigland@redhat.com> - 1.4-1
- Update to sanlock-1.4

* Fri Jun 10 2011 David Teigland <teigland@redhat.com> - 1.3-6
- fix python version, build i686 also

* Thu Jun 09 2011 David Teigland <teigland@redhat.com> - 1.3-5
- build exclusive x86_64, at least for now

* Thu Jun 09 2011 David Teigland <teigland@redhat.com> - 1.3-4
- build only x86_64, at least for now

* Thu Jun 09 2011 David Teigland <teigland@redhat.com> - 1.3-3
- fix libwdmd linking

* Thu Jun 09 2011 David Teigland <teigland@redhat.com> - 1.3-2
- shut up build warnings for wdmd and sanlock

* Thu Jun 09 2011 David Teigland <teigland@redhat.com> - 1.3-1
- Update to sanlock-1.3

* Mon May 09 2011 Chris Feist <cfeist@redhat.com> - 1.2.0-3
- Add python and python-devel to build requires

* Mon May 09 2011 Chris Feist <cfeist@redhat.com> - 1.2.0-1
- Use latest sources
- Sync .spec file

* Mon Apr  4 2011 Federico Simoncelli <fsimonce@redhat.com> - 1.1.0-3
- Add sanlock_admin.h header

* Fri Feb 18 2011 Chris Feist <cfeist@redhat.com> - 1.1.0-2
- Fixed install for wdmd

* Thu Feb 17 2011 Chris Feist <cfeist@redhat.com> - 1.1.0-1
- Updated to latest sources
- Now include wdmd

* Tue Feb 8 2011 Angus Salkeld <asalkeld@redhat.com> - 1.0-2
- SPEC: Add docs and make more consistent with the fedora template

* Mon Jan 10 2011 Fabio M. Di Nitto <fdinitto@redhat.com> - 1.0-1
- first cut at rpm packaging
